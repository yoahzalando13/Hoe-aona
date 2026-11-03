package com.hoeaona.mobile.ui;

import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisOut;
import com.hoeaona.mobile.model.AnalysisPage;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.util.FileParts;
import com.hoeaona.mobile.util.Format;
import okhttp3.MultipartBody;

import java.util.ArrayList;
import java.util.List;

/** Nouvelle publication : texte, image (8 Mo max) et analyse terminée jointe. */
public class CreatePostActivity extends AppCompatActivity {
    public static final String EXTRA_ANALYSIS_ID = "analysis_id";
    public static final String EXTRA_ANALYSIS_TITLE = "analysis_title";

    private TextInputEditText etBody;
    private ImageView ivImage;
    private TextView tvAnalysis;
    private MaterialButton btnPublish, btnRemoveImage;
    private Uri imageUri;
    private String analysisId;

    private final ActivityResultLauncher<String> pickImage = registerForActivityResult(
            new ActivityResultContracts.GetContent(), uri -> {
                if (uri == null) return;
                imageUri = uri;
                ivImage.setImageURI(uri);
                ivImage.setVisibility(View.VISIBLE);
                btnRemoveImage.setVisibility(View.VISIBLE);
            });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_create_post);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        etBody = findViewById(R.id.etBody);
        ivImage = findViewById(R.id.ivImage);
        tvAnalysis = findViewById(R.id.tvAnalysis);
        btnPublish = findViewById(R.id.btnPublish);
        btnRemoveImage = findViewById(R.id.btnRemoveImage);

        analysisId = getIntent().getStringExtra(EXTRA_ANALYSIS_ID);
        showAnalysis(getIntent().getStringExtra(EXTRA_ANALYSIS_TITLE));

        findViewById(R.id.btnPickImage).setOnClickListener(v -> pickImage.launch("image/*"));
        btnRemoveImage.setOnClickListener(v -> {
            imageUri = null;
            ivImage.setVisibility(View.GONE);
            btnRemoveImage.setVisibility(View.GONE);
        });
        findViewById(R.id.btnPickAnalysis).setOnClickListener(v -> pickAnalysis());
        btnPublish.setOnClickListener(v -> publish());
    }

    private void showAnalysis(String title) {
        tvAnalysis.setVisibility(analysisId != null ? View.VISIBLE : View.GONE);
        tvAnalysis.setText(getString(R.string.post_attached_analysis, title));
    }

    /** Seules les analyses terminées de son espace peuvent être jointes. */
    private void pickAnalysis() {
        ApiClient.getApiService().listAnalyses(null, null, null, null, 50, 0).enqueue(new ApiCallback<AnalysisPage>(this) {
            @Override
            public void onSuccess(AnalysisPage body) {
                List<AnalysisOut> done = new ArrayList<>();
                for (AnalysisOut a : body.items) if ("done".equals(a.status)) done.add(a);
                if (done.isEmpty()) {
                    Toast.makeText(CreatePostActivity.this, R.string.post_no_analysis, Toast.LENGTH_LONG).show();
                    return;
                }
                String[] labels = new String[done.size() + 1];
                labels[0] = getString(R.string.post_no_attachment);
                for (int i = 0; i < done.size(); i++) {
                    labels[i + 1] = done.get(i).title + " — " + Format.score(done.get(i).global_score);
                }
                new AlertDialog.Builder(CreatePostActivity.this).setTitle(R.string.post_attach_analysis)
                        .setItems(labels, (d, which) -> {
                            analysisId = which == 0 ? null : done.get(which - 1).id;
                            showAnalysis(which == 0 ? null : done.get(which - 1).title);
                        }).show();
            }
        });
    }

    private void publish() {
        String body = etBody.getText() != null ? etBody.getText().toString().trim() : "";
        if (body.isEmpty() && imageUri == null && analysisId == null) {
            Toast.makeText(this, R.string.post_empty, Toast.LENGTH_LONG).show();
            return;
        }
        MultipartBody.Part image = null;
        if (imageUri != null) {
            try {
                image = FileParts.part(this, "image", imageUri);
            } catch (Exception e) {
                Toast.makeText(this, R.string.error_file, Toast.LENGTH_LONG).show();
                return;
            }
        }
        btnPublish.setEnabled(false);
        ApiClient.getApiService().createPost(FileParts.text(body), FileParts.text(analysisId == null ? "" : analysisId), image)
                .enqueue(new ApiCallback<Post>(this) {
                    @Override
                    public void onSuccess(Post post) {
                        Toast.makeText(CreatePostActivity.this, R.string.post_published, Toast.LENGTH_SHORT).show();
                        finish();
                    }

                    @Override
                    public void onFinally() {
                        btnPublish.setEnabled(true);
                    }
                });
    }
}
