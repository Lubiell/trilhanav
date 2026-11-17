package io.github.lubiell.trilhanav;

import android.app.Notification;
import android.content.ComponentName;
import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import androidx.core.app.NotificationCompat;
import androidx.core.app.Person;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;

import java.util.ArrayDeque;

import java.util.List;

/**
 * "Acesso a notificações" (o usuário liga uma vez nas configurações do Android):
 *  - mensagens do WhatsApp / WhatsApp Business viram eventos para o app (só remetente e texto, nada é gravado);
 *  - o mesmo acesso libera a lista de players ativos, de onde sai a música que está tocando (Spotify etc.).
 */
public class TrilhaNotifService extends NotificationListenerService {
    public interface Sink {
        void onWhatsApp(JSObject msg);
        void onMedia(JSObject info);
        void onWaCall(JSObject call);
    }

    // ---- ligação pelo WhatsApp: a notificação de chamada traz quem liga e os botões Atender/Recusar/Desligar ----
    private static volatile String callKey = null;
    private static volatile android.app.PendingIntent waAnswer, waDecline, waHangup;
    private static final java.util.regex.Pattern CALL_TXT = java.util.regex.Pattern.compile(
        "(?i)(chamada|liga(ç|c)(ã|a)o).*(voz|v(í|i)deo|recebida|entrada)|(incoming|ongoing).*(voice|video)? ?call|em andamento|chamando|tocando");
    private static final java.util.regex.Pattern ANS = java.util.regex.Pattern.compile("(?i)^(atender|aceitar|answer|accept)");
    private static final java.util.regex.Pattern DEC = java.util.regex.Pattern.compile("(?i)^(recusar|rejeitar|decline|reject|ignorar)");
    private static final java.util.regex.Pattern HUP = java.util.regex.Pattern.compile("(?i)^(desligar|encerrar|hang ?up|end)");

    /** aciona o botão da notificação de chamada do WhatsApp: answer | decline | hangup */
    static String waAct(String act) {
        android.app.PendingIntent pi = "answer".equals(act) ? waAnswer : "decline".equals(act) ? (waDecline != null ? waDecline : waHangup) : (waHangup != null ? waHangup : waDecline);
        if (pi == null) return "sem botão para isso na notificação do WhatsApp";
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                android.app.ActivityOptions o = android.app.ActivityOptions.makeBasic();
                o.setPendingIntentBackgroundActivityStartMode(android.app.ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED);
                pi.send(null, 0, null, null, null, null, o.toBundle());
            } else {
                pi.send();
            }
            return null;
        } catch (Exception e) {
            return "o WhatsApp não aceitou: " + e.getMessage();
        }
    }

    /** é notificação de chamada? (categoria de chamada, estilo de chamada do Android 12+ ou texto "chamada de voz recebida") */
    private boolean handleCall(StatusBarNotification sbn, Notification n) {
        Bundle ex = n.extras;
        CharSequence t = ex == null ? null : ex.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence x = ex == null ? null : ex.getCharSequence(Notification.EXTRA_TEXT);
        boolean isCall = Notification.CATEGORY_CALL.equals(n.category)
            || (ex != null && (ex.containsKey("android.answerIntent") || ex.containsKey("android.declineIntent") || ex.containsKey("android.hangUpIntent")))
            || (x != null && CALL_TXT.matcher(x).find() && (n.flags & Notification.FLAG_ONGOING_EVENT) != 0);
        if (!isCall) return false;
        android.app.PendingIntent a = null, d = null, h = null;
        if (ex != null) {
            try { a = ex.getParcelable("android.answerIntent"); d = ex.getParcelable("android.declineIntent"); h = ex.getParcelable("android.hangUpIntent"); } catch (Exception ignored) { }
        }
        if (n.actions != null) for (Notification.Action ac : n.actions) {
            String l = ac.title == null ? "" : ac.title.toString().trim();
            if (a == null && ANS.matcher(l).find()) a = ac.actionIntent;
            else if (d == null && DEC.matcher(l).find()) d = ac.actionIntent;
            else if (h == null && HUP.matcher(l).find()) h = ac.actionIntent;
        }
        callKey = sbn.getKey();
        waAnswer = a; waDecline = d; waHangup = h;
        String txt = x == null ? "" : x.toString();
        boolean ringing = a != null;   // tocando = ainda tem o botão de atender
        JSObject o = new JSObject();
        o.put("state", ringing ? "ringing" : "offhook");
        o.put("name", clip(t == null ? "" : t.toString(), 80));
        o.put("video", txt.toLowerCase(java.util.Locale.ROOT).matches(".*(v(í|i)deo|video).*"));
        o.put("app", "com.whatsapp.w4b".equals(sbn.getPackageName()) ? "WhatsApp Business" : "WhatsApp");
        Sink s = sink;
        if (s != null) s.onWaCall(o);
        return true;
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        if (sbn == null || callKey == null || !callKey.equals(sbn.getKey())) return;
        callKey = null;
        waAnswer = waDecline = waHangup = null;
        JSObject o = new JSObject();
        o.put("state", "idle");
        Sink s = sink;
        if (s != null) s.onWaCall(o);
    }

    static volatile Sink sink;
    // diagnóstico (só contagens e nomes de pacote, nada do conteúdo): mostra no app por que o WhatsApp não aparece
    static volatile boolean connected = false;
    static volatile int seen = 0, seenWa = 0, sentWa = 0;
    static volatile String lastSkip = "";
    private static final ArrayDeque<String> lastPkgs = new ArrayDeque<>();

    static JSObject diag() {
        JSObject o = new JSObject();
        o.put("connected", connected);
        o.put("seen", seen);
        o.put("seenWa", seenWa);
        o.put("sentWa", sentWa);
        o.put("lastSkip", lastSkip);
        JSArray a = new JSArray();
        synchronized (lastPkgs) { for (String p : lastPkgs) a.put(p); }
        o.put("lastPkgs", a);
        return o;
    }
    private MediaSessionManager msm;
    private MediaController current;
    private final MediaController.Callback cb = new MediaController.Callback() {
        @Override public void onMetadataChanged(MediaMetadata m) { sendMedia(); }
        @Override public void onPlaybackStateChanged(PlaybackState s) { sendMedia(); }
        @Override public void onSessionDestroyed() { pick(null); }
    };
    private final MediaSessionManager.OnActiveSessionsChangedListener changed = this::pick;

    @Override
    public void onListenerConnected() {
        connected = true;
        try {
            msm = (MediaSessionManager) getSystemService(Context.MEDIA_SESSION_SERVICE);
            ComponentName me = new ComponentName(this, TrilhaNotifService.class);
            msm.addOnActiveSessionsChangedListener(changed, me);
            pick(msm.getActiveSessions(me));
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onListenerDisconnected() {
        connected = false;
        try {
            if (msm != null) msm.removeOnActiveSessionsChangedListener(changed);
            if (current != null) current.unregisterCallback(cb);
        } catch (Exception ignored) {
        }
        current = null;
    }

    /** escolhe o player que está tocando (ou o primeiro da lista) e passa a acompanhar ele */
    private void pick(List<MediaController> list) {
        try {
            if (list == null && msm != null) list = msm.getActiveSessions(new ComponentName(this, TrilhaNotifService.class));
        } catch (Exception e) {
            list = null;
        }
        MediaController best = null;
        if (list != null) {
            for (MediaController c : list) {
                PlaybackState s = c.getPlaybackState();
                if (s != null && s.getState() == PlaybackState.STATE_PLAYING) { best = c; break; }
                if (best == null) best = c;
            }
        }
        if (current != null) {
            try { current.unregisterCallback(cb); } catch (Exception ignored) { }
        }
        current = best;
        if (current != null) current.registerCallback(cb);
        sendMedia();
    }

    private void sendMedia() {
        Sink s = sink;
        if (s == null) return;
        JSObject o = new JSObject();
        MediaController c = current;
        if (c == null) {
            o.put("active", false);
        } else {
            MediaMetadata m = c.getMetadata();
            PlaybackState ps = c.getPlaybackState();
            o.put("active", true);
            o.put("pkg", c.getPackageName());
            o.put("title", m == null ? "" : clip(m.getString(MediaMetadata.METADATA_KEY_TITLE), 120));
            o.put("artist", m == null ? "" : clip(m.getString(MediaMetadata.METADATA_KEY_ARTIST), 120));
            o.put("playing", ps != null && ps.getState() == PlaybackState.STATE_PLAYING);
        }
        s.onMedia(o);
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null) return;
        String pkg = sbn.getPackageName();
        seen++;
        synchronized (lastPkgs) {
            lastPkgs.remove(pkg);
            lastPkgs.addFirst(pkg);
            while (lastPkgs.size() > 6) lastPkgs.removeLast();
        }
        if (!"com.whatsapp".equals(pkg) && !"com.whatsapp.w4b".equals(pkg)) return;
        seenWa++;
        Notification n = sbn.getNotification();
        if (n == null) { lastSkip = "sem notificação"; return; }
        if (handleCall(sbn, n)) { lastSkip = "chamada"; return; }
        // resumo do grupo ("3 mensagens de 2 conversas") e notificação fixa ("Verificando novas mensagens") não são mensagem
        if ((n.flags & Notification.FLAG_GROUP_SUMMARY) != 0) { lastSkip = "resumo do grupo"; return; }
        if ((n.flags & Notification.FLAG_ONGOING_EVENT) != 0) { lastSkip = "notificação fixa"; return; }
        String title = null, text = null;
        // o WhatsApp usa o estilo de conversa: a última mensagem e quem mandou ficam ali (o texto simples às vezes vem vazio)
        try {
            NotificationCompat.MessagingStyle ms = NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(n);
            if (ms != null && !ms.getMessages().isEmpty()) {
                NotificationCompat.MessagingStyle.Message m = ms.getMessages().get(ms.getMessages().size() - 1);
                Person who = m.getPerson();
                CharSequence conv = ms.getConversationTitle();
                String sender = who != null && who.getName() != null ? who.getName().toString() : null;
                if (conv != null && sender != null) title = conv + ": " + sender;
                else if (conv != null) title = conv.toString();
                else title = sender;
                if (m.getText() != null) text = m.getText().toString();
            }
        } catch (Exception ignored) {
        }
        Bundle ex = n.extras;
        if (ex != null) {
            if (title == null) {
                CharSequence t = ex.getCharSequence(Notification.EXTRA_TITLE);
                if (t != null) title = t.toString();
            }
            if (text == null) {
                CharSequence t = ex.getCharSequence(Notification.EXTRA_TEXT);
                if (t == null) t = ex.getCharSequence(Notification.EXTRA_BIG_TEXT);
                if (t == null) {
                    CharSequence[] lines = ex.getCharSequenceArray(Notification.EXTRA_TEXT_LINES);
                    if (lines != null && lines.length > 0) t = lines[lines.length - 1];
                }
                if (t != null) text = t.toString();
            }
        }
        if (title == null || text == null || text.isEmpty()) { lastSkip = "sem título ou texto"; return; }
        Sink s = sink;
        if (s == null) { lastSkip = "app fechado"; return; }
        JSObject o = new JSObject();
        o.put("app", "com.whatsapp.w4b".equals(pkg) ? "WhatsApp Business" : "WhatsApp");
        o.put("title", clip(title, 80));
        o.put("text", clip(text, 500));
        o.put("t", sbn.getPostTime());
        sentWa++;
        lastSkip = "";
        s.onWhatsApp(o);
    }

    private static String clip(String s, int n) {
        if (s == null) return "";
        return s.length() > n ? s.substring(0, n) : s;
    }
}
