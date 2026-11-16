package io.github.lubiell.trilhanav;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

import androidx.core.app.NotificationCompat;

import java.util.HashSet;
import java.util.Set;

import org.json.JSONObject;
import org.vosk.Model;
import org.vosk.Recognizer;
import org.vosk.android.RecognitionListener;
import org.vosk.android.SpeechService;
import org.vosk.android.StorageService;

/**
 * Assistente de voz sempre ligado, sem internet: Vosk com o modelo pequeno de português (dentro do APK) e uma gramática só
 * com as palavras de comando e os nomes da agenda. Roda como serviço em primeiro plano do tipo microfone, para seguir com a
 * tela apagada. Fica em pausa enquanto o próprio app fala (senão ouviria o "diga atender") e durante as ligações.
 * O que é ouvido não sai do aparelho: o texto vai só para o app, que só age se a frase começar com "trilha".
 */
public class TrilhaVoiceService extends Service implements RecognitionListener {
    public interface Sink {
        void onHeard(String text);
        void onVoiceState(String state, String msg);
    }

    static volatile Sink sink;
    static volatile String grammar = "[\"trilha\", \"[unk]\"]";
    private static TrilhaVoiceService self;
    private static final Set<String> holds = new HashSet<>();
    private static final Handler main = new Handler(Looper.getMainLooper());

    private Model model;
    private SpeechService speech;
    private boolean loading = false;

    static boolean running() {
        return self != null;
    }

    /** pausa/retoma a escuta por um motivo ("tts", "call", "listen"): só escuta quando não sobra motivo nenhum */
    static void hold(String why, boolean on) {
        main.post(() -> {
            if (on) holds.add(why); else holds.remove(why);
            TrilhaVoiceService s = self;
            if (s != null && s.speech != null) {
                s.speech.setPause(!holds.isEmpty());
                state(holds.isEmpty() ? "on" : "paused", "");
            }
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

    @Override
    public void onCreate() {
        super.onCreate();
        self = this;
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
                restart();
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

    private void restart() {
        try {
            if (speech != null) {
                speech.stop();
                speech.shutdown();
                speech = null;
            }
            Recognizer rec = new Recognizer(model, 16000.0f, grammar);
            speech = new SpeechService(rec, 16000.0f);
            speech.startListening(this);
            speech.setPause(!holds.isEmpty());
            state(holds.isEmpty() ? "on" : "paused", "");
        } catch (Exception e) {
            state("error", "microfone: " + e.getMessage());
        }
    }

    private void deliver(String json) {
        try {
            String t = new JSONObject(json).optString("text", "").trim();
            if (t.isEmpty() || t.equals("[unk]")) return;
            Sink k = sink;
            if (k != null) k.onHeard(t);
        } catch (Exception ignored) {
        }
    }

    @Override public void onResult(String hypothesis) { deliver(hypothesis); }
    @Override public void onFinalResult(String hypothesis) { deliver(hypothesis); }
    @Override public void onPartialResult(String hypothesis) { }
    @Override public void onError(Exception e) { state("error", "microfone: " + e.getMessage()); }
    @Override public void onTimeout() { }

    @Override
    public void onDestroy() {
        if (speech != null) {
            speech.stop();
            speech.shutdown();
            speech = null;
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
