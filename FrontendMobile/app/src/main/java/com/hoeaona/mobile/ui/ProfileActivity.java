package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.model.PostPage;
import com.hoeaona.mobile.model.PublicUser;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.util.Format;

import java.util.HashMap;
import java.util.Map;

/** Profil public et publications ; pour son propre compte, modification du profil et du mot de passe. */
public class ProfileActivity extends AppCompatActivity {
    public static final String EXTRA_ID = "user_id";

    private String userId;
    private TextView tvName, tvOrganization, tvBio, tvMeta;
    private View cardEdit;
    private TextInputEditText etName, etOrganization, etBio, etCurrentPassword, etNewPassword;
    private PostAdapter adapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_profile);
        userId = getIntent().getStringExtra(EXTRA_ID);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        tvName = findViewById(R.id.tvName);
        tvOrganization = findViewById(R.id.tvOrganization);
        tvBio = findViewById(R.id.tvBio);
        tvMeta = findViewById(R.id.tvMeta);
        cardEdit = findViewById(R.id.cardEdit);
        etName = findViewById(R.id.etName);
        etOrganization = findViewById(R.id.etOrganization);
        etBio = findViewById(R.id.etBio);
        etCurrentPassword = findViewById(R.id.etCurrentPassword);
        etNewPassword = findViewById(R.id.etNewPassword);

        RecyclerView recycler = findViewById(R.id.recyclerPosts);
        recycler.setLayoutManager(new LinearLayoutManager(this));
        recycler.setNestedScrollingEnabled(false);
        adapter = new PostAdapter(new PostActions(this, this, new PostActions.Listener() {
            @Override public void onPostChanged(Post post) { adapter.replace(post); }
            @Override public void onPostDeleted(Post post) { adapter.remove(post); }
        }));
        recycler.setAdapter(adapter);

        findViewById(R.id.btnSaveProfile).setOnClickListener(v -> saveProfile());
        findViewById(R.id.btnChangePassword).setOnClickListener(v -> changePassword());

        ApiClient.getApiService().getMe().enqueue(new ApiCallback<User>(this) {
            @Override
            public void onSuccess(User me) {
                boolean self = me.id.equals(userId);
                cardEdit.setVisibility(self ? View.VISIBLE : View.GONE);
                if (self) {
                    etName.setText(me.display_name);
                    etOrganization.setText(me.organization);
                    etBio.setText(me.bio);
                }
            }
        });
        load();
    }

    private void load() {
        ApiClient.getApiService().getProfile(userId).enqueue(new ApiCallback<PublicUser>(this) {
            @Override
            public void onSuccess(PublicUser u) {
                tvName.setText(u.display_name);
                tvOrganization.setText(u.organization);
                tvOrganization.setVisibility(u.organization == null || u.organization.isEmpty() ? View.GONE : View.VISIBLE);
                tvBio.setText(u.bio);
                tvBio.setVisibility(u.bio == null || u.bio.isEmpty() ? View.GONE : View.VISIBLE);
                String role = getString("admin".equals(u.role) ? R.string.role_admin
                        : "reader".equals(u.role) ? R.string.role_reader : R.string.role_media);
                tvMeta.setText(getString(R.string.profile_meta, role, Format.date(u.created_at),
                        getResources().getQuantityString(R.plurals.posts_count, u.posts_count, u.posts_count)));
            }
        });
        ApiClient.getApiService().listPosts(null, userId, 50, 0).enqueue(new ApiCallback<PostPage>(this) {
            @Override
            public void onSuccess(PostPage body) {
                adapter.setPosts(body.items);
            }
        });
    }

    private String text(TextInputEditText field) {
        return field.getText() != null ? field.getText().toString().trim() : "";
    }

    private void saveProfile() {
        Map<String, String> patch = new HashMap<>();
        patch.put("display_name", text(etName));
        patch.put("organization", text(etOrganization));
        patch.put("bio", text(etBio));
        ApiClient.getApiService().updateMe(patch).enqueue(new ApiCallback<User>(this) {
            @Override
            public void onSuccess(User body) {
                Toast.makeText(ProfileActivity.this, R.string.saved, Toast.LENGTH_SHORT).show();
                load();
            }
        });
    }

    private void changePassword() {
        String current = etCurrentPassword.getText() != null ? etCurrentPassword.getText().toString() : "";
        String next = etNewPassword.getText() != null ? etNewPassword.getText().toString() : "";
        if (next.length() < 8) {
            etNewPassword.setError(getString(R.string.login_password_short));
            return;
        }
        Map<String, String> payload = new HashMap<>();
        payload.put("current_password", current);
        payload.put("new_password", next);
        ApiClient.getApiService().changePassword(payload).enqueue(new ApiCallback<Void>(this) {
            @Override
            public void onSuccess(Void body) {
                etCurrentPassword.setText("");
                etNewPassword.setText("");
                Toast.makeText(ProfileActivity.this, R.string.profile_password_changed, Toast.LENGTH_SHORT).show();
            }
        });
    }
}
