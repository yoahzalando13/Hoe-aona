package com.hoeaona.mobile.verify;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AppNotification;
import com.hoeaona.mobile.util.Format;
import retrofit2.Response;

import java.util.List;

/** Récupère les nouvelles notifications du serveur et les affiche comme notifications Android. */
public final class VerificationNotifier {
    public static final String CHANNEL = "verifications";

    private VerificationNotifier() {}

    public static void createChannel(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(CHANNEL,
                    context.getString(R.string.notif_channel), NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription(context.getString(R.string.notif_channel_desc));
            context.getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    /** Appel bloquant : à lancer hors du fil principal. */
    public static void poll(Context context) {
        try {
            Response<List<AppNotification>> response = ApiClient.getApiService().notifications(true).execute();
            if (!response.isSuccessful() || response.body() == null) return;
            for (AppNotification n : response.body()) show(context, n);
        } catch (Exception ignored) {
            // hors ligne : nouvel essai au prochain cycle
        }
    }

    public static String title(Context c, AppNotification n) {
        switch (n.kind) {
            case "verification_request": return c.getString(R.string.notif_request_title);
            case "verification_accepted": return c.getString(R.string.notif_accepted_title);
            case "verification_released": return c.getString(R.string.notif_released_title);
            case "verification_completed": return c.getString(R.string.notif_completed_title);
            case "verification_cancelled": return c.getString(R.string.notif_cancelled_title);
            default: return c.getString(R.string.app_name);
        }
    }

    public static String body(Context c, AppNotification n) {
        if (n.request == null) return "";
        switch (n.kind) {
            case "verification_request":
                return c.getString(R.string.notif_request_body, n.request.place_label, n.request.claim);
            case "verification_accepted":
                return c.getString(R.string.notif_accepted_body, n.request.verifier_name, n.request.claim);
            case "verification_completed":
                return c.getString(R.string.notif_completed_body, Format.outcome(c, n.request.outcome), n.request.claim);
            default:
                return n.request.claim;
        }
    }

    private static void show(Context context, AppNotification n) {
        if (n.request == null || !NotificationManagerCompat.from(context).areNotificationsEnabled()) return;
        Intent intent = new Intent(context, VerificationActivity.class)
                .putExtra(VerificationActivity.EXTRA_ID, n.request.id)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent pending = PendingIntent.getActivity(context, n.id.hashCode(), intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String body = body(context, n);
        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_notification)
                .setColor(context.getColor(R.color.primary))
                .setContentTitle(title(context, n))
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setContentIntent(pending);
        try {
            // Une seule notification par demande : la demande acceptée remplace l'annonce.
            NotificationManagerCompat.from(context).notify(n.request.id.hashCode(), builder.build());
        } catch (SecurityException ignored) {
            // permission de notification retirée entre-temps
        }
    }

    /** Une demande prise par quelqu'un d'autre disparaît aussi du volet de notifications. */
    public static void dismiss(Context context, String requestId) {
        NotificationManagerCompat.from(context).cancel(requestId.hashCode());
    }
}
