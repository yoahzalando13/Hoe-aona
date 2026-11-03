package com.hoeaona.mobile.api;

import android.content.Intent;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.lifecycle.Lifecycle;
import androidx.lifecycle.LifecycleOwner;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.HoeApp;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.auth.LoginActivity;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Rappel Retrofit commun : ignore les réponses arrivées après la fermeture de l'écran,
 * affiche le message d'erreur du backend (champ « detail ») et renvoie vers la connexion sur 401.
 */
public abstract class ApiCallback<T> implements Callback<T> {
    @Nullable private final LifecycleOwner owner;

    protected ApiCallback(@Nullable LifecycleOwner owner) {
        this.owner = owner;
    }

    public abstract void onSuccess(T body);

    /** Par défaut : message court. Les écrans peuvent le remplacer. */
    public void onError(int code, String message) {
        Toast.makeText(HoeApp.get(), message, Toast.LENGTH_LONG).show();
    }

    public void onFinally() {}

    /** Les écrans de connexion reçoivent aussi des 401 (mauvais mot de passe) : ils le désactivent. */
    protected boolean redirectOnUnauthorized() {
        return true;
    }

    private boolean alive() {
        return owner == null || owner.getLifecycle().getCurrentState().isAtLeast(Lifecycle.State.CREATED);
    }

    @Override
    public void onResponse(Call<T> call, Response<T> response) {
        if (!alive()) return;
        onFinally();
        if (response.isSuccessful()) {
            onSuccess(response.body());
            return;
        }
        if (response.code() == 401 && redirectOnUnauthorized()) {
            ApiClient.clearSession();
            Intent intent = new Intent(HoeApp.get(), LoginActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            HoeApp.get().startActivity(intent);
        }
        onError(response.code(), errorMessage(response));
    }

    @Override
    public void onFailure(Call<T> call, Throwable t) {
        if (!alive() || call.isCanceled()) return;
        onFinally();
        onError(0, HoeApp.get().getString(R.string.error_network, t.getMessage()));
    }

    public static String errorMessage(Response<?> response) {
        try (okhttp3.ResponseBody body = response.errorBody()) {
            if (body != null) {
                JsonElement json = new Gson().fromJson(body.string(), JsonElement.class);
                if (json.isJsonObject()) {
                    JsonElement detail = ((JsonObject) json).get("detail");
                    if (detail != null && detail.isJsonPrimitive()) return detail.getAsString();
                    if (detail != null && detail.isJsonArray() && ((JsonArray) detail).size() > 0) {
                        JsonObject first = ((JsonArray) detail).get(0).getAsJsonObject();
                        if (first.has("msg")) return first.get("msg").getAsString();
                    }
                }
            }
        } catch (Exception ignored) {
            // corps illisible : message générique ci-dessous
        }
        return HoeApp.get().getString(R.string.error_http, response.code());
    }
}
