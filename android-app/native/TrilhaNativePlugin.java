package io.github.lubiell.trilhanav;

import android.Manifest;
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
    permissions = { @Permission(alias = "notifications", strings = { Manifest.permission.POST_NOTIFICATIONS }) }
)
public class TrilhaNativePlugin extends Plugin {
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
        tts = new TextToSpeech(getContext(), status -> {
            if (status != TextToSpeech.SUCCESS) return;
            tts.setLanguage(new Locale("pt", "BR"));
            tts.setAudioAttributes(attrs);
            tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override public void onStart(String id) { focusOn(); }
                @Override public void onDone(String id) { focusOff(); }
                @Override public void onError(String id) { focusOff(); }
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

    @Override
    protected void handleOnDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
    }
}
