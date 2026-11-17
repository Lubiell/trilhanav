package io.github.lubiell.trilhanav;

import android.Manifest;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.telephony.SmsManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.IntentFilter;
import android.content.pm.PackageInfo;
import android.database.Cursor;
import android.os.Handler;
import android.os.Looper;
import android.provider.ContactsContract;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.telecom.TelecomManager;
import android.telephony.TelephonyManager;
import androidx.core.app.NotificationManagerCompat;
import androidx.core.content.ContextCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.ArrayList;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Base64;
import android.view.KeyEvent;

import androidx.core.content.FileProvider;

import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.File;
import java.io.FileOutputStream;
import java.util.Locale;

/**
 * Funções nativas do TrilhaNav: voz do copiloto (funciona com a tela apagada e baixa a música enquanto fala),
 * comandos de mídia para o player ativo (Spotify etc.), abrir outro app e entregar arquivos exportados
 * (o WebView não baixa arquivos: o GPX/ZIP vai para a tela de compartilhar do Android).
 */
@CapacitorPlugin(
    name = "TrilhaNative",
    permissions = {
        @Permission(alias = "notifications", strings = { Manifest.permission.POST_NOTIFICATIONS }),
        @Permission(alias = "phone", strings = { Manifest.permission.READ_PHONE_STATE, Manifest.permission.CALL_PHONE,
            Manifest.permission.ANSWER_PHONE_CALLS, Manifest.permission.READ_CALL_LOG }),
        @Permission(alias = "contacts", strings = { Manifest.permission.READ_CONTACTS }),
        @Permission(alias = "mic", strings = { Manifest.permission.RECORD_AUDIO }),
        @Permission(alias = "sms", strings = { Manifest.permission.SEND_SMS })
    }
)
public class TrilhaNativePlugin extends Plugin implements TrilhaNotifService.Sink, TrilhaVoiceService.Sink {
    private static final String UPDATE_PREFIX = "https://raw.githubusercontent.com/Lubiell/trilhanav/apk/";
    private final Handler main = new Handler(Looper.getMainLooper());
    private BroadcastReceiver phoneRx;
    private String lastState = "";
    private SpeechRecognizer rec;
    private PluginCall listenCall;
    private boolean updating = false;
    private SensorManager sensors;
    private SensorEventListener impactL;
    private float impactG = 4f;
    private long lastImpact = 0;
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private String pendingText = null;
    private float pendingVolume = 1f;
    private AudioManager audio;
    private AudioFocusRequest focus;
    private final AudioAttributes attrs = new AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
        .build();

    @Override
    public void load() {
        audio = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
        TrilhaNotifService.sink = this;
        TrilhaVoiceService.sink = this;
        // depois de atualizar o app o Android às vezes não religa o acesso a notificações: pede para religar
        try {
            if (Build.VERSION.SDK_INT >= 24 && NotificationManagerCompat.getEnabledListenerPackages(getContext()).contains(getContext().getPackageName()))
                android.service.notification.NotificationListenerService.requestRebind(new ComponentName(getContext(), TrilhaNotifService.class));
        } catch (Exception ignored) {
        }
        startPhoneWatch();
        tts = new TextToSpeech(getContext(), status -> {
            if (status != TextToSpeech.SUCCESS) return;
            tts.setLanguage(new Locale("pt", "BR"));
            tts.setAudioAttributes(attrs);
            tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                // enquanto o app fala, o assistente não escuta (senão ouviria o próprio "diga atender")
                private final java.util.Set<String> live = java.util.Collections.synchronizedSet(new java.util.HashSet<>());
                private void upd() { TrilhaVoiceService.hold("tts", !live.isEmpty()); }
                @Override public void onStart(String id) { live.add(id); upd(); focusOn(); }
                @Override public void onDone(String id) { live.remove(id); main.postDelayed(this::upd, 300); focusOff(); }
                @Override public void onError(String id) { live.remove(id); upd(); focusOff(); }
                @Override public void onStop(String id, boolean interrupted) { live.remove(id); upd(); focusOff(); }
            });
            ttsReady = true;
            if (pendingText != null) {
                speakNow(pendingText, pendingVolume, false);
                pendingText = null;
            }
        });
    }

    private void focusOn() {
        if (Build.VERSION.SDK_INT >= 26 && audio != null) {
            if (focus == null) {
                focus = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(attrs)
                    .build();
            }
            audio.requestAudioFocus(focus);
        }
    }

    private void focusOff() {
        if (Build.VERSION.SDK_INT >= 26 && audio != null && focus != null) {
            audio.abandonAudioFocusRequest(focus);
        }
    }

    private void speakNow(String text, float volume, boolean urgent) {
        Bundle p = new Bundle();
        p.putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, volume);
        tts.speak(text, urgent ? TextToSpeech.QUEUE_FLUSH : TextToSpeech.QUEUE_ADD, p, "tn" + System.nanoTime());
    }

    @PluginMethod
    public void speak(PluginCall call) {
        String text = call.getString("text");
        if (text == null || text.isEmpty()) {
            call.reject("sem texto");
            return;
        }
        float volume = call.getFloat("volume", 1f);
        boolean urgent = call.getBoolean("urgent", false);
        if (!ttsReady) {
            pendingText = text;
            pendingVolume = volume;
        } else {
            speakNow(text, volume, urgent);
        }
        call.resolve();
    }

    /** Manda a tecla de mídia ao player que estiver ativo: playpause, play, pause, next, previous, stop. */
    @PluginMethod
    public void mediaKey(PluginCall call) {
        String key = call.getString("key", "");
        int code;
        switch (key) {
            case "playpause": code = KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE; break;
            case "play": code = KeyEvent.KEYCODE_MEDIA_PLAY; break;
            case "pause": code = KeyEvent.KEYCODE_MEDIA_PAUSE; break;
            case "next": code = KeyEvent.KEYCODE_MEDIA_NEXT; break;
            case "previous": code = KeyEvent.KEYCODE_MEDIA_PREVIOUS; break;
            case "stop": code = KeyEvent.KEYCODE_MEDIA_STOP; break;
            default: call.reject("tecla desconhecida: " + key); return;
        }
        long t = SystemClock.uptimeMillis();
        audio.dispatchMediaKeyEvent(new KeyEvent(t, t, KeyEvent.ACTION_DOWN, code, 0));
        audio.dispatchMediaKeyEvent(new KeyEvent(t, t, KeyEvent.ACTION_UP, code, 0));
        call.resolve();
    }

    /** Abre outro app pelo nome do pacote; se não estiver instalado, abre a página dele na loja. */
    @PluginMethod
    public void openApp(PluginCall call) {
        String pkg = call.getString("package");
        if (pkg == null || !pkg.matches("[A-Za-z0-9_.]+")) {
            call.reject("pacote inválido");
            return;
        }
        Intent i = getContext().getPackageManager().getLaunchIntentForPackage(pkg);
        if (i == null) {
            Intent store = new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + pkg));
            store.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                getContext().startActivity(store);
            } catch (Exception e) {
                call.reject("app não instalado");
                return;
            }
            call.resolve();
            return;
        }
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(i);
        call.resolve();
    }

    /** Abre um link https em outro app (Waze, Google Maps) ou no navegador. Só aceita https. */
    @PluginMethod
    public void openUrl(PluginCall call) {
        String url = call.getString("url");
        if (url == null || !url.startsWith("https://") || url.length() > 2000) {
            call.reject("link inválido");
            return;
        }
        Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            getContext().startActivity(i);
        } catch (Exception e) {
            call.reject("nenhum app abre este link");
            return;
        }
        call.resolve();
    }

    /**
     * Entrega um arquivo gerado pelo app (GPX, ZIP, backup): grava no cache e abre a tela de compartilhar,
     * de onde dá para salvar em Arquivos, mandar para o Drive, WhatsApp etc.
     */
    @PluginMethod
    public void shareFile(PluginCall call) {
        String name = call.getString("name");
        String data = call.getString("data");
        String mime = call.getString("mime", "application/octet-stream");
        if (name == null || data == null || !name.matches("[A-Za-z0-9_. ()-]{1,80}") || name.startsWith(".")) {
            call.reject("arquivo inválido");
            return;
        }
        try {
            File dir = new File(getContext().getCacheDir(), "export");
            if (!dir.exists() && !dir.mkdirs()) {
                call.reject("sem acesso ao armazenamento");
                return;
            }
            File[] old = dir.listFiles();
            if (old != null) {
                for (File f : old) {
                    f.delete();
                }
            }
            File out = new File(dir, name);
            try (FileOutputStream os = new FileOutputStream(out)) {
                os.write(Base64.decode(data, Base64.DEFAULT));
            }
            Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", out);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType(mime);
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.setClipData(ClipData.newRawUri(name, uri));
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            Intent chooser = Intent.createChooser(send, "Salvar ou enviar " + name);
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            getContext().startActivity(chooser);
            call.resolve();
        } catch (Exception e) {
            call.reject("não consegui preparar o arquivo: " + e.getMessage());
        }
    }

    /** Android 13+: pede permissão da notificação do serviço de GPS. */
    @PluginMethod
    public void requestNotifications(PluginCall call) {
        if (Build.VERSION.SDK_INT < 33 || getPermissionState("notifications") == PermissionState.GRANTED) {
            call.resolve();
            return;
        }
        requestPermissionForAlias("notifications", call, "notifCallback");
    }

    @PermissionCallback
    private void notifCallback(PluginCall call) {
        call.resolve();
    }

    // ---------------------------------------------------------------- ligações

    private boolean has(String alias) {
        return getPermissionState(alias) == PermissionState.GRANTED;
    }

    /** escuta o estado do telefone (tocando / em ligação / livre) e manda para o app com o nome do contato */
    private void startPhoneWatch() {
        if (phoneRx != null || ContextCompat.checkSelfPermission(getContext(), Manifest.permission.READ_PHONE_STATE) != android.content.pm.PackageManager.PERMISSION_GRANTED) return;
        phoneRx = new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent i) {
                String st = i.getStringExtra(TelephonyManager.EXTRA_STATE);
                @SuppressWarnings("deprecation") String num = i.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER);
                String s = TelephonyManager.EXTRA_STATE_RINGING.equals(st) ? "ringing" : TelephonyManager.EXTRA_STATE_OFFHOOK.equals(st) ? "offhook" : "idle";
                // o Android manda o aviso duas vezes (com e sem o número): só repassa o que traz novidade
                if (s.equals(lastState) && num == null) return;
                lastState = s;
                TrilhaVoiceService.hold("call", "offhook".equals(s));   // em ligação o microfone é da ligação
                JSObject o = new JSObject();
                o.put("state", s);
                o.put("number", num == null ? "" : num);
                o.put("name", num == null ? "" : contactName(num));
                notifyListeners("call", o, true);
            }
        };
        ContextCompat.registerReceiver(getContext(), phoneRx, new IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED), ContextCompat.RECEIVER_EXPORTED);
    }

    private String contactName(String number) {
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.READ_CONTACTS) != android.content.pm.PackageManager.PERMISSION_GRANTED) return "";
        try (Cursor c = getContext().getContentResolver().query(
                Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number)),
                new String[] { ContactsContract.PhoneLookup.DISPLAY_NAME }, null, null, null)) {
            if (c != null && c.moveToFirst()) return c.getString(0);
        } catch (Exception ignored) {
        }
        return "";
    }

    /** situação das permissões e acessos especiais */
    @PluginMethod
    public void phoneStatus(PluginCall call) {
        JSObject o = new JSObject();
        o.put("phone", has("phone"));
        o.put("contacts", has("contacts"));
        o.put("mic", has("mic"));
        o.put("notifAccess", NotificationManagerCompat.getEnabledListenerPackages(getContext()).contains(getContext().getPackageName()));
        o.put("speech", SpeechRecognizer.isRecognitionAvailable(getContext()));
        o.put("installAllowed", Build.VERSION.SDK_INT < 26 || getContext().getPackageManager().canRequestPackageInstalls());
        o.put("sdk", Build.VERSION.SDK_INT);
        o.put("voiceOn", TrilhaVoiceService.running());
        o.put("notif", TrilhaNotifService.diag());
        call.resolve(o);
    }

    @PluginMethod
    public void requestPhone(PluginCall call) {
        requestPermissionForAliases(new String[] { "phone", "contacts", "mic" }, call, "phoneCallback");
    }

    @PermissionCallback
    private void phoneCallback(PluginCall call) {
        startPhoneWatch();
        phoneStatus(call);
    }

    /** abre a tela do Android onde se libera o "acesso a notificações" */
    @PluginMethod
    public void openNotifAccess(PluginCall call) {
        Intent i = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try { getContext().startActivity(i); } catch (Exception e) { openAppSettings(call); return; }
        call.resolve();
    }

    /** informações do app (Android 13+: é aqui o "Permitir configurações restritas") */
    @PluginMethod
    public void openAppSettings(PluginCall call) {
        Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getContext().getPackageName()));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try { getContext().startActivity(i); } catch (Exception e) { call.reject("não abriu"); return; }
        call.resolve();
    }

    @PluginMethod
    public void answerCall(PluginCall call) {
        if (Build.VERSION.SDK_INT < 26) { call.reject("Android antigo demais para atender pelo app"); return; }
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.ANSWER_PHONE_CALLS) != android.content.pm.PackageManager.PERMISSION_GRANTED) { call.reject("sem permissão"); return; }
        try {
            ((TelecomManager) getContext().getSystemService(Context.TELECOM_SERVICE)).acceptRingingCall();
            call.resolve();
        } catch (Exception e) {
            call.reject("o aparelho não deixou atender: " + e.getMessage());
        }
    }

    /** recusa a ligação que está tocando ou desliga a que está em curso */
    @PluginMethod
    public void endCall(PluginCall call) {
        if (Build.VERSION.SDK_INT < 28) { call.reject("Android antigo demais para recusar pelo app"); return; }
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.ANSWER_PHONE_CALLS) != android.content.pm.PackageManager.PERMISSION_GRANTED) { call.reject("sem permissão"); return; }
        try {
            boolean ok = ((TelecomManager) getContext().getSystemService(Context.TELECOM_SERVICE)).endCall();
            if (ok) call.resolve(); else call.reject("o aparelho não deixou encerrar");
        } catch (Exception e) {
            call.reject("o aparelho não deixou encerrar: " + e.getMessage());
        }
    }

    @PluginMethod
    public void placeCall(PluginCall call) {
        String num = call.getString("number", "");
        if (!num.matches("[+0-9*#() .-]{2,30}")) { call.reject("número inválido"); return; }
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.CALL_PHONE) != android.content.pm.PackageManager.PERMISSION_GRANTED) { call.reject("sem permissão"); return; }
        Intent i = new Intent(Intent.ACTION_CALL, Uri.fromParts("tel", num.replaceAll("[ ().-]", ""), null));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try { getContext().startActivity(i); call.resolve(); } catch (Exception e) { call.reject("não consegui ligar: " + e.getMessage()); }
    }

    /** busca na agenda por nome (até 20 números) */
    @PluginMethod
    public void findContacts(PluginCall call) {
        String q = call.getString("q", "").trim();
        if (q.isEmpty() || q.length() > 60) { call.reject("busca vazia"); return; }
        if (!has("contacts")) { call.reject("sem permissão"); return; }
        JSArray out = new JSArray();
        try (Cursor c = getContext().getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                new String[] { ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER },
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " LIKE ?", new String[] { "%" + q + "%" },
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC")) {
            while (c != null && c.moveToNext() && out.length() < 20) {
                JSObject o = new JSObject();
                o.put("name", c.getString(0));
                o.put("number", c.getString(1));
                out.put(o);
            }
        } catch (Exception e) {
            call.reject("não consegui ler a agenda");
            return;
        }
        JSObject r = new JSObject();
        r.put("list", out);
        call.resolve(r);
    }

    // ---------------------------------------------------------------- voz

    /** escuta uma frase em pt-BR e devolve as transcrições possíveis (a melhor primeiro) */
    @PluginMethod
    public void listen(PluginCall call) {
        if (!has("mic")) { call.reject("sem permissão do microfone"); return; }
        if (!SpeechRecognizer.isRecognitionAvailable(getContext())) { call.reject("reconhecimento de voz indisponível"); return; }
        final int ms = Math.max(2000, Math.min(15000, call.getInt("ms", 7000)));
        main.post(() -> {
            if (listenCall != null) { listenCall.reject("cancelado"); listenCall = null; }
            if (tts != null) tts.stop();
            if (rec == null) {
                rec = SpeechRecognizer.createSpeechRecognizer(getContext());
                rec.setRecognitionListener(new RecognitionListener() {
                    @Override public void onReadyForSpeech(Bundle b) { }
                    @Override public void onBeginningOfSpeech() { }
                    @Override public void onRmsChanged(float v) { }
                    @Override public void onBufferReceived(byte[] b) { }
                    @Override public void onEndOfSpeech() { }
                    @Override public void onPartialResults(Bundle b) { }
                    @Override public void onEvent(int t, Bundle b) { }
                    @Override public void onError(int err) { finishListen(null, err); }
                    @Override public void onResults(Bundle b) { finishListen(b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION), 0); }
                });
            }
            listenCall = call;
            TrilhaVoiceService.hold("listen", true);   // o microfone é de um só por vez
            Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR");
            i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
            rec.startListening(i);
            final PluginCall mine = call;
            main.postDelayed(() -> { if (listenCall == mine && rec != null) rec.stopListening(); }, ms);
        });
    }

    private void finishListen(ArrayList<String> texts, int err) {
        TrilhaVoiceService.hold("listen", false);
        PluginCall c = listenCall;
        listenCall = null;
        if (c == null) return;
        if (texts == null || texts.isEmpty()) {
            c.reject(err == SpeechRecognizer.ERROR_NO_MATCH || err == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ? "não entendi" : "erro de voz " + err);
            return;
        }
        JSObject o = new JSObject();
        o.put("texts", new JSArray(texts));
        c.resolve(o);
    }

    // ---------------------------------------------------------------- assistente sempre ligado (Vosk, sem internet)

    private static String grammarOf(PluginCall call) {
        java.util.LinkedHashSet<String> w = new java.util.LinkedHashSet<>();
        JSArray a = call.getArray("words", new JSArray());
        for (int i = 0; i < a.length() && w.size() < 800; i++) {
            String s = a.optString(i, "").toLowerCase(Locale.ROOT).trim();
            if (s.matches("[\\p{L}]{1,20}")) w.add(s);
        }
        org.json.JSONArray g = new org.json.JSONArray();
        for (String s : w) g.put(s);
        g.put("[unk]");
        return g.toString();
    }

    @PluginMethod
    public void voiceStart(PluginCall call) {
        if (!has("mic")) { call.reject("sem permissão do microfone"); return; }
        TrilhaVoiceService.useBt = call.getBoolean("bt", false);
        TrilhaVoiceService.setGrammar(grammarOf(call));
        try {
            ContextCompat.startForegroundService(getContext(), new Intent(getContext(), TrilhaVoiceService.class));
            call.resolve();
        } catch (Exception e) {
            call.reject("não consegui ligar o assistente: " + e.getMessage());
        }
    }

    /** usa (ou não) o microfone do fone/intercom Bluetooth para o assistente */
    @PluginMethod
    public void voiceBt(PluginCall call) {
        TrilhaVoiceService.setBt(call.getBoolean("on", false));
        call.resolve();
    }

    @PluginMethod
    public void voiceStop(PluginCall call) {
        getContext().stopService(new Intent(getContext(), TrilhaVoiceService.class));
        call.resolve();
    }

    @PluginMethod
    public void voiceWords(PluginCall call) {
        TrilhaVoiceService.setGrammar(grammarOf(call));
        call.resolve();
    }

    @Override
    public void onHeard(String text) {
        JSObject o = new JSObject();
        o.put("text", text);
        notifyListeners("heard", o);
    }

    @Override
    public void onVoiceState(String state, String msg) {
        JSObject o = new JSObject();
        o.put("state", state);
        o.put("msg", msg);
        notifyListeners("voice", o, true);
    }

    /** a agenda inteira (nome + número), para a lista do app e os nomes do assistente de voz */
    @PluginMethod
    public void listContacts(PluginCall call) {
        if (!has("contacts")) { call.reject("sem permissão da agenda"); return; }
        new Thread(() -> {
            JSArray out = new JSArray();
            java.util.HashSet<String> dup = new java.util.HashSet<>();
            try (Cursor c = getContext().getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[] { ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME, ContactsContract.CommonDataKinds.Phone.NUMBER },
                    null, null, ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC")) {
                while (c != null && c.moveToNext() && out.length() < 3000) {
                    String name = c.getString(0), num = c.getString(1);
                    if (name == null || num == null) continue;
                    String key = name + "|" + num.replaceAll("[^+0-9]", "");
                    if (!dup.add(key)) continue;
                    JSObject o = new JSObject();
                    o.put("name", name);
                    o.put("number", num);
                    out.put(o);
                }
            } catch (Exception e) {
                call.reject("não consegui ler a agenda");
                return;
            }
            JSObject r = new JSObject();
            r.put("list", out);
            call.resolve(r);
        }).start();
    }

    // ---------------------------------------------------------------- aviso de queda (SOS)

    /**
     * Liga/desliga a escuta do acelerômetro: um pico acima de g (4 = normal, 3 = alta) vira o evento "impact".
     * A decisão (estava andando? ficou parado?) é do app, que tem o GPS. Funciona com a tela apagada porque o app
     * já roda serviços em primeiro plano (GPS e voz).
     */
    @PluginMethod
    public void crashArm(PluginCall call) {
        final boolean on = call.getBoolean("on", false);
        impactG = Math.max(2f, Math.min(8f, call.getFloat("g", 4f)));
        main.post(() -> {
            if (sensors == null) sensors = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
            if (impactL != null) {
                sensors.unregisterListener(impactL);
                impactL = null;
            }
            if (!on || sensors == null) return;
            Sensor acc = sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            if (acc == null) return;
            impactL = new SensorEventListener() {
                @Override
                public void onSensorChanged(SensorEvent e) {
                    double g = Math.sqrt(e.values[0] * e.values[0] + e.values[1] * e.values[1] + e.values[2] * e.values[2]) / 9.81;
                    long now = System.currentTimeMillis();
                    if (g >= impactG && now - lastImpact > 3000) {
                        lastImpact = now;
                        JSObject o = new JSObject();
                        o.put("g", Math.round(g * 10) / 10.0);
                        o.put("t", now);
                        notifyListeners("impact", o, true);
                    }
                }
                @Override public void onAccuracyChanged(Sensor s, int a) { }
            };
            sensors.registerListener(impactL, acc, SensorManager.SENSOR_DELAY_GAME);
        });
        JSObject r = new JSObject();
        r.put("sensor", ((SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE)).getDefaultSensor(Sensor.TYPE_ACCELEROMETER) != null);
        call.resolve(r);
    }

    @PluginMethod
    public void requestSms(PluginCall call) {
        if (has("sms")) { JSObject r = new JSObject(); r.put("granted", true); call.resolve(r); return; }
        requestPermissionForAlias("sms", call, "smsCallback");
    }

    @PermissionCallback
    private void smsCallback(PluginCall call) {
        JSObject r = new JSObject();
        r.put("granted", has("sms"));
        call.resolve(r);
    }

    /** manda o mesmo SMS para até 3 números (aviso de queda ou o teste) */
    @PluginMethod
    public void sendSms(PluginCall call) {
        if (!has("sms")) { call.reject("sem permissão de SMS"); return; }
        String text = call.getString("text", "");
        JSArray nums = call.getArray("numbers", new JSArray());
        if (text.isEmpty() || text.length() > 480 || nums.length() == 0) { call.reject("mensagem inválida"); return; }
        try {
            SmsManager sm = Build.VERSION.SDK_INT >= 31 ? getContext().getSystemService(SmsManager.class) : SmsManager.getDefault();
            ArrayList<String> parts = sm.divideMessage(text);
            int sent = 0;
            for (int i = 0; i < nums.length() && i < 3; i++) {
                String n = nums.optString(i, "").replaceAll("[^+0-9]", "");
                if (n.length() < 3 || n.length() > 20) continue;
                sm.sendMultipartTextMessage(n, null, parts, null, null);
                sent++;
            }
            JSObject r = new JSObject();
            r.put("sent", sent);
            call.resolve(r);
        } catch (Exception e) {
            call.reject("SMS falhou: " + e.getMessage());
        }
    }

    // ---------------------------------------------------------------- música

    /** volume da música: dir = up | down */
    @PluginMethod
    public void volume(PluginCall call) {
        int d = "down".equals(call.getString("dir")) ? AudioManager.ADJUST_LOWER : AudioManager.ADJUST_RAISE;
        audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, d, AudioManager.FLAG_SHOW_UI);
        call.resolve();
    }

    /** manda "tocar" direto para o Spotify, que começa a tocar em segundo plano sem abrir na frente */
    @PluginMethod
    public void spotifyPlay(PluginCall call) {
        try {
            long t = SystemClock.uptimeMillis();
            for (int a : new int[] { KeyEvent.ACTION_DOWN, KeyEvent.ACTION_UP }) {
                Intent i = new Intent(Intent.ACTION_MEDIA_BUTTON);
                i.setPackage("com.spotify.music");
                i.putExtra(Intent.EXTRA_KEY_EVENT, new KeyEvent(t, t, a, KeyEvent.KEYCODE_MEDIA_PLAY, 0));
                getContext().sendBroadcast(i);
            }
            call.resolve();
        } catch (Exception e) {
            call.reject("Spotify não respondeu");
        }
    }

    @Override
    public void onWhatsApp(JSObject msg) {
        notifyListeners("whatsapp", msg, true);
    }

    @Override
    public void onWaCall(JSObject call) {
        String st = call.getString("state", "idle");
        TrilhaVoiceService.hold("call", "offhook".equals(st));   // em ligação o microfone é da ligação
        notifyListeners("wacall", call, true);
    }

    /** atende / recusa / desliga a ligação do WhatsApp pelo botão da notificação dela */
    @PluginMethod
    public void waCallAction(PluginCall call) {
        String act = call.getString("act", "");
        if (!act.matches("answer|decline|hangup")) { call.reject("ação inválida"); return; }
        String err = TrilhaNotifService.waAct(act);
        if (err == null) call.resolve(); else call.reject(err);
    }

    @Override
    public void onMedia(JSObject info) {
        notifyListeners("media", info, true);
    }

    // ---------------------------------------------------------------- atualização

    @PluginMethod
    public void appInfo(PluginCall call) {
        try {
            PackageInfo pi = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
            JSObject o = new JSObject();
            o.put("version", pi.versionName);
            o.put("code", Build.VERSION.SDK_INT >= 28 ? pi.getLongVersionCode() : pi.versionCode);
            call.resolve(o);
        } catch (Exception e) {
            call.reject("sem versão");
        }
    }

    /**
     * Baixa o APK novo do branch "apk" do repositório (só de lá), confere o SHA-256 e abre o instalador do Android.
     * O Android pede a confirmação; os dados do app ficam (mesma assinatura).
     */
    @PluginMethod
    public void installApk(PluginCall call) {
        final String url = call.getString("url", "");
        final String sha = call.getString("sha256", "").toLowerCase(Locale.ROOT);
        if (!url.startsWith(UPDATE_PREFIX) || !url.substring(UPDATE_PREFIX.length()).matches("trilhanav-[0-9.]+\\.apk") || !sha.matches("[0-9a-f]{64}")) {
            call.reject("atualização inválida");
            return;
        }
        if (Build.VERSION.SDK_INT >= 26 && !getContext().getPackageManager().canRequestPackageInstalls()) {
            Intent i = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getContext().getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try { getContext().startActivity(i); } catch (Exception ignored) { }
            call.reject("permita instalar apps do TrilhaNav e toque de novo");
            return;
        }
        if (updating) { call.reject("já está baixando"); return; }
        updating = true;
        new Thread(() -> {
            File out = new File(new File(getContext().getCacheDir(), "update"), "trilhanav-update.apk");
            try {
                File dir = out.getParentFile();
                if (dir != null && !dir.exists() && !dir.mkdirs()) throw new Exception("sem espaço");
                HttpURLConnection con = (HttpURLConnection) new URL(url).openConnection();
                con.setConnectTimeout(20000);
                con.setReadTimeout(30000);
                if (con.getResponseCode() != 200) throw new Exception("HTTP " + con.getResponseCode());
                long total = con.getContentLengthLong(), got = 0;
                int lastPct = -1;
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                try (InputStream in = con.getInputStream(); FileOutputStream os = new FileOutputStream(out)) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        os.write(buf, 0, n);
                        md.update(buf, 0, n);
                        got += n;
                        if (got > 200L * 1024 * 1024) throw new Exception("arquivo grande demais");
                        int pct = total > 0 ? (int) (got * 100 / total) : -1;
                        if (pct != lastPct) {
                            lastPct = pct;
                            JSObject p = new JSObject();
                            p.put("pct", pct);
                            notifyListeners("update", p);
                        }
                    }
                }
                StringBuilder hex = new StringBuilder();
                for (byte b : md.digest()) hex.append(String.format("%02x", b));
                if (!hex.toString().equals(sha)) {
                    out.delete();
                    throw new Exception("o arquivo baixado não confere (SHA-256 diferente)");
                }
                Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", out);
                Intent i = new Intent(Intent.ACTION_VIEW);
                i.setDataAndType(uri, "application/vnd.android.package-archive");
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                getContext().startActivity(i);
                call.resolve();
            } catch (Exception e) {
                call.reject("atualização falhou: " + e.getMessage());
            } finally {
                updating = false;
            }
        }).start();
    }

    @Override
    protected void handleOnDestroy() {
        TrilhaNotifService.sink = null;
        TrilhaVoiceService.sink = null;
        if (impactL != null && sensors != null) {
            sensors.unregisterListener(impactL);
            impactL = null;
        }
        if (phoneRx != null) {
            try { getContext().unregisterReceiver(phoneRx); } catch (Exception ignored) { }
            phoneRx = null;
        }
        if (rec != null) {
            final SpeechRecognizer r = rec;
            rec = null;
            main.post(r::destroy);
        }
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
    }
}
