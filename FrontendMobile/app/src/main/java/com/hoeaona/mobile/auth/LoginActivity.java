package com.hoeaona.mobile.auth;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.button.MaterialButtonToggleGroup;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.MainActivity;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AuthConfig;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.util.Lang;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.HashMap;
import java.util.Map;

public class LoginActivity extends AppCompatActivity {

    private TextInputEditText etEmail, etPassword, etDisplayName, etOrganization, etServer;
    private MaterialButton btnLogin;
    private TextView tvToggleMode, tvFirstAccount;
    private LinearLayout layoutRegisterFields, layoutServer;
    private boolean isRegisterMode = false;
    private AuthConfig authConfig;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);

        etEmail = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);
        etDisplayName = findViewById(R.id.etDisplayName);
        etOrganization = findViewById(R.id.etOrganization);
        etServer = findViewById(R.id.etServer);
        btnLogin = findViewById(R.id.btnLogin);
        tvToggleMode = findViewById(R.id.tvToggleMode);
        tvFirstAccount = findViewById(R.id.tvFirstAccount);
        layoutRegisterFields = findViewById(R.id.layoutRegisterFields);
        layoutServer = findViewById(R.id.layoutServer);

        MaterialButtonToggleGroup langGroup = findViewById(R.id.langGroup);
        String lang = Lang.current();
        langGroup.check("mg".equals(lang) ? R.id.btnLangMg : "en".equals(lang) ? R.id.btnLangEn : R.id.btnLangFr);
        langGroup.addOnButtonCheckedListener((group, checkedId, isChecked) -> {
            if (!isChecked) return;
            Lang.set(checkedId == R.id.btnLangMg ? "mg" : checkedId == R.id.btnLangEn ? "en" : "fr");
        });

        etServer.setText(ApiClient.getServerUrl());
        findViewById(R.id.tvServerToggle).setOnClickListener(v ->
                layoutServer.setVisibility(layoutServer.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE));
        findViewById(R.id.btnSaveServer).setOnClickListener(v -> {
            String url = etServer.getText() != null ? etServer.getText().toString().trim() : "";
            if (url.isEmpty()) return;
            ApiClient.setServerUrl(url);
            etServer.setText(ApiClient.getServerUrl());
            Toast.makeText(this, R.string.login_server_saved, Toast.LENGTH_SHORT).show();
            checkSession();
        });

        tvToggleMode.setOnClickListener(v -> setRegisterMode(!isRegisterMode));
        btnLogin.setOnClickListener(v -> submit());
        checkSession();
    }

    /** Session encore valide : on passe directement à l'accueil. Sinon on lit la configuration des comptes. */
    private void checkSession() {
        ApiClient.getApiService().getMe().enqueue(new Callback<User>() {
            @Override
            public void onResponse(Call<User> call, Response<User> response) {
                if (response.isSuccessful() && response.body() != null) {
                    openMain();
                }
            }

            @Override
            public void onFailure(Call<User> call, Throwable t) {}
        });
        ApiClient.getApiService().getAuthConfig().enqueue(new ApiCallback<AuthConfig>(this) {
            @Override
            public void onSuccess(AuthConfig body) {
                authConfig = body;
                tvToggleMode.setVisibility(body.allow_registration ? View.VISIBLE : View.GONE);
                tvFirstAccount.setVisibility(body.has_users ? View.GONE : View.VISIBLE);
                if (!body.has_users) setRegisterMode(true);
            }

            @Override
            public void onError(int code, String message) {
                layoutServer.setVisibility(View.VISIBLE);
                Toast.makeText(LoginActivity.this, getString(R.string.login_server_unreachable, message),
                        Toast.LENGTH_LONG).show();
            }
        });
    }

    private void setRegisterMode(boolean register) {
        if (register && authConfig != null && !authConfig.allow_registration) return;
        isRegisterMode = register;
        layoutRegisterFields.setVisibility(register ? View.VISIBLE : View.GONE);
        btnLogin.setText(register ? R.string.login_register : R.string.login_submit);
        tvToggleMode.setText(register ? R.string.login_have_account : R.string.login_no_account);
    }

    private String text(TextInputEditText field) {
        return field.getText() != null ? field.getText().toString().trim() : "";
    }

    private void submit() {
        String email = text(etEmail);
        String password = etPassword.getText() != null ? etPassword.getText().toString() : "";
        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, R.string.login_fill_fields, Toast.LENGTH_SHORT).show();
            return;
        }
        Map<String, String> payload = new HashMap<>();
        payload.put("email", email);
        payload.put("password", password);
        Call<User> call;
        if (isRegisterMode) {
            String displayName = text(etDisplayName);
            if (displayName.length() < 2) {
                etDisplayName.setError(getString(R.string.login_name_required));
                return;
            }
            if (password.length() < 8) {
                etPassword.setError(getString(R.string.login_password_short));
                return;
            }
            payload.put("display_name", displayName);
            payload.put("organization", text(etOrganization));
            call = ApiClient.getApiService().register(payload);
        } else {
            call = ApiClient.getApiService().login(payload);
        }
        btnLogin.setEnabled(false);
        call.enqueue(new ApiCallback<User>(this) {
            @Override
            public void onSuccess(User body) {
                openMain();
            }

            @Override
            public void onFinally() {
                btnLogin.setEnabled(true);
            }

            @Override
            protected boolean redirectOnUnauthorized() {
                return false;
            }
        });
    }

    private void openMain() {
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }
}
