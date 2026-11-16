package io.github.lubiell.trilhanav;

import android.app.Notification;
import android.content.ComponentName;
import android.content.Context;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
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
