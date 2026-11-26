package io.github.lubiell.trilhanav;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioDeviceInfo;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import androidx.core.app.NotificationCompat;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.json.JSONArray;
import org.json.JSONObject;
import org.vosk.Model;
import org.vosk.Recognizer;
import org.vosk.android.StorageService;

/**
 * Assistente de voz sempre ligado, sem internet: Vosk com o modelo pequeno de português (dentro do APK) e uma gramática só
 * com as palavras de comando e os nomes da agenda. Roda como serviço em primeiro plano do tipo microfone, para seguir com a
 * tela apagada. Fica em pausa enquanto o próprio app fala (senão ouviria o "diga atender") e durante as ligações.
 * O que é ouvido não sai do aparelho: o texto vai só para o app, que só age se a frase começar com "trilha".
 *
 * Microfone do fone/intercom Bluetooth (cfg "voiceBt"): liga o canal de voz do Bluetooth (SCO) e grava dele. Enquanto o canal
 * estiver ligado o Android manda a música também por ele, com qualidade de ligação (mono): é o preço de ouvir pelo capacete.
 * A captura é feita aqui (AudioRecord próprio) e não pelo SpeechService do Vosk, para poder escolher o microfone.
 */
public class TrilhaVoiceService extends Service {
    public interface Sink {
        /** text = o mais provável; alts = até 3 hipóteses, a mais provável primeiro */
        void onHeard(String text, List<String> alts);
        void onVoiceState(String state, String msg);
    }

    static volatile Sink sink;
    static volatile String grammar = "[\"trilha\", \"[unk]\"]";
    static volatile boolean useBt = false;
    /** (2.7.11) sensibilidade "alta" do "Trilha": ganho automático do Android (se houver) e o som ×2 antes do Vosk */
    static volatile boolean boost = false;
    /** com vento ou motor o Vosk quase não acha o silêncio do fim da frase: a frase fecha quando o que foi ouvido para de mudar
     *  por STILL_MS, e no máximo MAX_SEC depois de começar a ouvir alguma coisa (silêncio e ruído sem palavra não contam) */
    static final int MAX_SEC = 8, STILL_MS = 1200;
    private static TrilhaVoiceService self;
    private static final Set<String> holds = new HashSet<>();
    private static final Handler main = new Handler(Looper.getMainLooper());

    private Model model;
    private Recognizer rec;
    private final Object recLock = new Object();
    private Thread loop;
    private volatile boolean running = false;
    private volatile boolean paused = false;
    private boolean loading = false;
    private AudioManager am;
    private boolean btOn = false;
    private AudioDeviceInfo btIn = null;
    private int savedCallVol = -1;
    private final Runnable btTick = new Runnable() {
        @Override public void run() { if (self == TrilhaVoiceService.this) { applyBt(); main.postDelayed(this, 15000); } }
    };

    static boolean running() {
        return self != null;
    }

    static boolean onHeadset() {
        TrilhaVoiceService s = self;
        return s != null && s.btOn;
    }

    /** pausa/retoma a escuta por um motivo ("tts", "call", "listen"): só escuta quando não sobra motivo nenhum.
     *  Em ligação e na escuta do Google o microfone é solto de verdade (outra pessoa precisa dele). */
    static void hold(String why, boolean on) {
        main.post(() -> {
            if (on) holds.add(why); else holds.remove(why);
            TrilhaVoiceService s = self;
            if (s == null || s.model == null) return;
            boolean needMic = !holds.contains("call") && !holds.contains("listen");
            if (!needMic && s.running) { s.stopLoop(); s.applyBt(); }
            else if (needMic && !s.running) { s.applyBt(); s.startLoop(); }
            s.paused = !holds.isEmpty();
            if (!s.paused) synchronized (s.recLock) { if (s.rec != null) s.rec.reset(); }
            s.report();
        });
    }

    /** (2.7.11) muda a sensibilidade; recomeça a captura para ligar/desligar o ganho automático */
    static void setBoost(boolean on) {
        if (boost == on) return;
        boost = on;
        main.post(() -> {
            TrilhaVoiceService s = self;
            if (s != null && s.model != null) s.restartLoop();
        });
    }

    /** liga/desliga o microfone do fone Bluetooth */
    static void setBt(boolean on) {
        useBt = on;
        main.post(() -> {
            TrilhaVoiceService s = self;
            if (s != null && s.model != null) { s.applyBt(); s.restartLoop(); }
        });
    }

    /** troca a gramática (palavras de comando + nomes) e recomeça a escuta com ela */
    static void setGrammar(String g) {
        grammar = g;
        main.post(() -> {
            TrilhaVoiceService s = self;
            if (s != null && s.model != null) s.restart();
        });
    }

    private static void state(String st, String msg) {
        Sink k = sink;
        if (k != null) k.onVoiceState(st, msg == null ? "" : msg);
    }

    private void report() {
        state(paused || !running ? "paused" : "on", btOn ? "fone" : "celular");
    }

    @Override
    public void onCreate() {
        super.onCreate();
        self = this;
        am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startAsForeground();
        if (model == null && !loading) {
            loading = true;
            state("loading", "carregando o modelo de voz");
            // o modelo vem nos assets do APK; na 1ª vez é copiado para a pasta do app (precisa do arquivo "uuid")
            StorageService.unpack(this, "model-pt", "model", m -> {
                loading = false;
                model = m;
                applyBt();
                restart();
                main.postDelayed(btTick, 15000);
            }, e -> {
                loading = false;
                state("error", "modelo de voz: " + e.getMessage());
            });
        }
        return START_STICKY;
    }

    private void startAsForeground() {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel("tn_voz") == null) {
            NotificationChannel ch = new NotificationChannel("tn_voz", "TrilhaNav (voz)", NotificationManager.IMPORTANCE_LOW);
            ch.setShowBadge(false);
            nm.createNotificationChannel(ch);
        }
        Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());
        PendingIntent pi = open == null ? null : PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE);
        Notification n = new NotificationCompat.Builder(this, "tn_voz")
            .setContentTitle("TrilhaNav: assistente de voz ligado")
            .setContentText("Diga \"Trilha\" e o comando. Sem internet: nada sai do celular.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setContentIntent(pi)
            .build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(4242, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        else startForeground(4242, n);
    }

    /** liga o canal de voz do fone Bluetooth quando pedido e disponível (fora de ligação, que cuida dele sozinha) */
    @SuppressWarnings("deprecation")
    private void applyBt() {
        if (am == null) return;
        boolean want = useBt && !holds.contains("call");
        boolean was = btOn;
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                AudioDeviceInfo bt = null;
                for (AudioDeviceInfo d : am.getAvailableCommunicationDevices()) if (d.getType() == AudioDeviceInfo.TYPE_BLUETOOTH_SCO) { bt = d; break; }
                if (want && bt != null) {
                    AudioDeviceInfo cur = am.getCommunicationDevice();
                    if (cur == null || cur.getId() != bt.getId()) am.setCommunicationDevice(bt);
                    btOn = true;
                } else if (btOn) {
                    am.clearCommunicationDevice();
                    btOn = false;
                } else btOn = false;
            } else {
                if (want && am.isBluetoothScoAvailableOffCall() && hasBtInput()) {
                    if (!am.isBluetoothScoOn()) { am.setMode(AudioManager.MODE_IN_COMMUNICATION); am.startBluetoothSco(); am.setBluetoothScoOn(true); }
                    btOn = true;
                } else if (btOn) {
                    am.setBluetoothScoOn(false); am.stopBluetoothSco(); am.setMode(AudioManager.MODE_NORMAL);
                    btOn = false;
                }
            }
        } catch (Exception e) {
            btOn = false;
        }
        if (was != btOn) scoVolume(btOn);
        btIn = null;
        if (btOn) for (AudioDeviceInfo d : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) if (d.getType() == AudioDeviceInfo.TYPE_BLUETOOTH_SCO) { btIn = d; break; }
        if (was != btOn && running) { restartLoop(); }
        else report();
    }

    /** (2.7.9) com o canal de ligação (SCO) aberto a música sai por ele e com o volume de ligação, que costuma estar mais baixo:
     *  ao abrir, põe o volume de ligação na mesma proporção do volume da música (nunca abaixa o que o dono deixou); ao fechar, volta. */
    private void scoVolume(boolean on) {
        try {
            if (on && savedCallVol < 0) {
                savedCallVol = am.getStreamVolume(AudioManager.STREAM_VOICE_CALL);
                int mMax = Math.max(1, am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)), vMax = am.getStreamMaxVolume(AudioManager.STREAM_VOICE_CALL);
                int want = Math.round((float) am.getStreamVolume(AudioManager.STREAM_MUSIC) * vMax / mMax);
                am.setStreamVolume(AudioManager.STREAM_VOICE_CALL, Math.min(vMax, Math.max(savedCallVol, want)), 0);
            } else if (!on && savedCallVol >= 0) {
                am.setStreamVolume(AudioManager.STREAM_VOICE_CALL, savedCallVol, 0);
                savedCallVol = -1;
            }
        } catch (Exception e) {
            // sem permissão de mexer no volume de ligação (Não perturbe) ou aparelho que não deixa: segue sem ajustar
        }
    }

    private boolean hasBtInput() {
        for (AudioDeviceInfo d : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) if (d.getType() == AudioDeviceInfo.TYPE_BLUETOOTH_SCO) return true;
        return false;
    }

    private void restart() {
        try {
            stopLoop();
            synchronized (recLock) {
                if (rec != null) rec.close();
                rec = new Recognizer(model, 16000.0f, grammar);
                // até 3 hipóteses: se a mais provável não for um comando, o app tenta as outras
                rec.setMaxAlternatives(3);
            }
            paused = !holds.isEmpty();
            if (!holds.contains("call") && !holds.contains("listen")) startLoop();
            report();
        } catch (Exception e) {
            state("error", "microfone: " + e.getMessage());
        }
    }

    private void restartLoop() {
        if (model == null) return;
        stopLoop();
        if (!holds.contains("call") && !holds.contains("listen")) startLoop();
        report();
    }

    /** grava 16 kHz mono do microfone escolhido e entrega ao Vosk; o texto reconhecido vai para o app */
    private void startLoop() {
        if (running || rec == null) return;
        running = true;
        final boolean bt = btOn;
        final AudioDeviceInfo dev = btIn;
        loop = new Thread(() -> {
            AudioRecord ar = null;
            android.media.audiofx.AutomaticGainControl agc = null;
            android.media.audiofx.NoiseSuppressor ns = null;
            try {
                int min = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
                ar = new AudioRecord(bt ? MediaRecorder.AudioSource.VOICE_COMMUNICATION : MediaRecorder.AudioSource.VOICE_RECOGNITION,
                    16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, Math.max(min, 8192));
                if (bt && dev != null) ar.setPreferredDevice(dev);
                if (ar.getState() != AudioRecord.STATE_INITIALIZED) { state("error", "microfone não abriu"); return; }
                final boolean hi = boost;
                if (hi) {
                    try {
                        if (android.media.audiofx.AutomaticGainControl.isAvailable()) {
                            agc = android.media.audiofx.AutomaticGainControl.create(ar.getAudioSessionId());
                            if (agc != null) agc.setEnabled(true);
                        }
                    } catch (Exception e) { agc = null; }
                    // (2.7.12) no bolso e com vento: também o supressor de ruído do Android, se o aparelho tiver
                    try {
                        if (android.media.audiofx.NoiseSuppressor.isAvailable()) {
                            ns = android.media.audiofx.NoiseSuppressor.create(ar.getAudioSessionId());
                            if (ns != null) ns.setEnabled(true);
                        }
                    } catch (Exception e) { ns = null; }
                }
                ar.startRecording();
                short[] buf = new short[2048];
                long fed = 0, still = 0;
                String lastP = "";
                int tick = 0;
                while (running) {
                    int n = ar.read(buf, 0, buf.length);
                    if (n <= 0 || paused) { fed = 0; still = 0; lastP = ""; continue; }
                    if (hi) for (int k = 0; k < n; k++) { int v = buf[k] * 2; buf[k] = (short) (v > 32767 ? 32767 : (v < -32768 ? -32768 : v)); }
                    String res = null;
                    synchronized (recLock) {
                        if (rec != null) {
                            if (rec.acceptWaveForm(buf, n)) { res = rec.getResult(); fed = 0; still = 0; lastP = ""; }
                            else {
                                if (!lastP.isEmpty()) { fed += n; still += n; }
                                if (++tick % 4 == 0) {   // ~0,5 s
                                    String p = partialText(rec.getPartialResult());
                                    if (p.isEmpty()) { fed = 0; still = 0; lastP = ""; }
                                    else if (!p.equals(lastP)) { lastP = p; still = 0; }
                                }
                                if (!lastP.isEmpty() && (still >= 16L * STILL_MS || fed >= 16000L * MAX_SEC)) {
                                    res = rec.getFinalResult(); fed = 0; still = 0; lastP = "";
                                }
                            }
                        }
                    }
                    if (res != null) deliver(res);
                }
            } catch (SecurityException e) {
                state("error", "sem permissão do microfone");
            } catch (Exception e) {
                state("error", "microfone: " + e.getMessage());
            } finally {
                if (agc != null) { try { agc.release(); } catch (Exception ignored) { } }
                if (ns != null) { try { ns.release(); } catch (Exception ignored) { } }
                if (ar != null) { try { ar.stop(); } catch (Exception ignored) { } ar.release(); }
                running = false;
            }
        }, "trilha-voz");
        loop.start();
    }

    private void stopLoop() {
        running = false;
        Thread t = loop;
        loop = null;
        if (t != null) { try { t.join(1500); } catch (InterruptedException ignored) { } }
    }

    /** texto da hipótese parcial do Vosk, sem os [unk] */
    private static String partialText(String json) {
        try {
            return new JSONObject(json).optString("partial", "").replace("[unk]", " ").trim();
        } catch (Exception e) {
            return "";
        }
    }

    private void deliver(String json) {
        try {
            JSONObject o = new JSONObject(json);
            List<String> alts = new ArrayList<>();
            JSONArray a = o.optJSONArray("alternatives");
            if (a != null) {
                for (int k = 0; k < a.length() && alts.size() < 3; k++) {
                    JSONObject h = a.optJSONObject(k);
                    String t = h == null ? "" : h.optString("text", "").trim();
                    if (!t.isEmpty() && !t.equals("[unk]") && !alts.contains(t)) alts.add(t);
                }
            } else {
                String t = o.optString("text", "").trim();
                if (!t.isEmpty() && !t.equals("[unk]")) alts.add(t);
            }
            if (alts.isEmpty()) return;
            final String best = alts.get(0);
            final List<String> all = alts;
            Sink k = sink;
            if (k != null) main.post(() -> k.onHeard(best, all));
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onDestroy() {
        main.removeCallbacks(btTick);
        stopLoop();
        boolean b = useBt; useBt = false; applyBt(); useBt = b;
        synchronized (recLock) {
            if (rec != null) { rec.close(); rec = null; }
        }
        if (model != null) {
            model.close();
            model = null;
        }
        self = null;
        state("off", "");
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
