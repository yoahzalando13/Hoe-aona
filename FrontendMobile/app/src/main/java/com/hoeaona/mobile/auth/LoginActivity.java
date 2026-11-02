package com.hoeaona.mobile.auth;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.MainActivity;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.util.SvgLoader;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.HashMap;
import java.util.Map;

public class LoginActivity extends AppCompatActivity {

    private TextInputEditText etEmail, etPassword, etDisplayName, etOrganization;
    private MaterialButton btnLogin;
    private TextView tvToggleMode;
    private LinearLayout layoutRegisterFields;
    private boolean isRegisterMode = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);

        etEmail = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);
        etDisplayName = findViewById(R.id.etDisplayName);
        etOrganization = findViewById(R.id.etOrganization);
        btnLogin = findViewById(R.id.btnLogin);
        tvToggleMode = findViewById(R.id.tvToggleMode);
        layoutRegisterFields = findViewById(R.id.layoutRegisterFields);

        ImageView ivLogo = findViewById(R.id.ivLogo);
        if (ivLogo != null) {
            SvgLoader.loadSvg(ivLogo, "logo-hoe-aona.svg");
        }

        ApiClient.getApiService().getMe().enqueue(new Callback<User>() {
            @Override
            public void onResponse(Call<User> call, Response<User> response) {
                if (response.isSuccessful() && response.body() != null) {
                    startActivity(new Intent(LoginActivity.this, MainActivity.class));
                    finish();
                }
            }

            @Override
            public void onFailure(Call<User> call, Throwable t) {}
        });

        tvToggleMode.setOnClickListener(v -> {
            isRegisterMode = !isRegisterMode;
            if (isRegisterMode) {
                layoutRegisterFields.setVisibility(View.VISIBLE);
                btnLogin.setText("S'inscrire");
                tvToggleMode.setText("Déjà un compte ? Se connecter");
            } else {
                layoutRegisterFields.setVisibility(View.GONE);
                btnLogin.setText("Se connecter");
                tvToggleMode.setText("Pas de compte ? S'inscrire");
            }
        });

        btnLogin.setOnClickListener(v -> {
            String email = etEmail.getText() != null ? etEmail.getText().toString().trim() : "";
            String password = etPassword.getText() != null ? etPassword.getText().toString().trim() : "";

            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(LoginActivity.this, "Veuillez remplir tous les champs obligatoires", Toast.LENGTH_SHORT).show();
                return;
            }

            if (isRegisterMode) {
                String displayName = etDisplayName.getText() != null ? etDisplayName.getText().toString().trim() : "";
                String organization = etOrganization.getText() != null ? etOrganization.getText().toString().trim() : "";
                if (displayName.isEmpty()) {
                    Toast.makeText(LoginActivity.this, "Veuillez entrer un nom d'affichage", Toast.LENGTH_SHORT).show();
                    return;
                }
                Map<String, String> payload = new HashMap<>();
                payload.put("email", email);
                payload.put("password", password);
                payload.put("display_name", displayName);
                payload.put("organization", organization);

                ApiClient.getApiService().register(payload).enqueue(new Callback<User>() {
                    @Override
                    public void onResponse(Call<User> call, Response<User> response) {
                        if (response.isSuccessful() && response.body() != null) {
                            Toast.makeText(LoginActivity.this, "Inscription réussie !", Toast.LENGTH_SHORT).show();
                            startActivity(new Intent(LoginActivity.this, MainActivity.class));
                            finish();
                        } else {
                            Toast.makeText(LoginActivity.this, "Erreur d'inscription", Toast.LENGTH_SHORT).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<User> call, Throwable t) {
                        Toast.makeText(LoginActivity.this, "Erreur réseau : " + t.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                });

            } else {
                Map<String, String> credentials = new HashMap<>();
                credentials.put("email", email);
                credentials.put("password", password);

                ApiClient.getApiService().login(credentials).enqueue(new Callback<User>() {
                    @Override
                    public void onResponse(Call<User> call, Response<User> response) {
                        if (response.isSuccessful() && response.body() != null) {
                            Toast.makeText(LoginActivity.this, "Connexion réussie", Toast.LENGTH_SHORT).show();
                            startActivity(new Intent(LoginActivity.this, MainActivity.class));
                            finish();
                        } else {
                            Toast.makeText(LoginActivity.this, "Identifiants incorrects", Toast.LENGTH_SHORT).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<User> call, Throwable t) {
                        Toast.makeText(LoginActivity.this, "Erreur réseau : " + t.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                });
            }
        });
    }
}
