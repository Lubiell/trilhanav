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

import com.getcapacitor.JSObject;

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
        Sink s = sink;
        if (s == null || sbn == null) return;
        String pkg = sbn.getPackageName();
        if (!"com.whatsapp".equals(pkg) && !"com.whatsapp.w4b".equals(pkg)) return;
        Notification n = sbn.getNotification();
        if (n == null) return;
        // resumo do grupo ("3 mensagens de 2 conversas") e notificações fixas ("Verificando novas mensagens") não são mensagem
        if ((n.flags & Notification.FLAG_GROUP_SUMMARY) != 0 || (n.flags & Notification.FLAG_ONGOING_EVENT) != 0) return;
        Bundle ex = n.extras;
        if (ex == null) return;
        CharSequence title = ex.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence text = ex.getCharSequence(Notification.EXTRA_TEXT);
        if (title == null || text == null) return;
        JSObject o = new JSObject();
        o.put("app", "com.whatsapp.w4b".equals(pkg) ? "WhatsApp Business" : "WhatsApp");
        o.put("title", clip(title.toString(), 80));
        o.put("text", clip(text.toString(), 500));
        o.put("t", sbn.getPostTime());
        s.onWhatsApp(o);
    }

    private static String clip(String s, int n) {
        if (s == null) return "";
        return s.length() > n ? s.substring(0, n) : s;
    }
}
