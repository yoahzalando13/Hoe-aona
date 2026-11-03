package com.hoeaona.mobile.verify;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Verification;
import com.hoeaona.mobile.ui.ResultActivity;
import com.hoeaona.mobile.util.FileParts;
import com.hoeaona.mobile.util.Format;
import com.hoeaona.mobile.util.ImageLoader;
import okhttp3.MultipartBody;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;

import android.os.Build;
import com.google.gson.JsonObject;
import okhttp3.RequestBody;

import java.io.File;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Locale;

/**
 * Détail d'une demande. Selon le rôle : le destinataire accepte ou refuse, le vérificateur se rend sur place
 * et confirme si l'information est correcte, le demandeur suit l'avancement et peut annuler.
 */
public class VerificationActivity extends AppCompatActivity {
    public static final String EXTRA_ID = "verification_id";

    private String id;
    private Verification current;
    private TextView tvStatus, tvClaim, tvDetails, tvPlace, tvPeople, tvOutcome, tvConsensus, tvPrivacy;
    private MapView map;
    private ImageView ivReportPhoto;
    private LinearLayout layoutReports;
    private String captureToken;
    private LinearLayout layoutRecipientActions, layoutVerifierActions, layoutReportForm, layoutResult;
    private MaterialButton btnCancel, btnOpenAnalysis, btnSendReport;
    private RadioGroup rgOutcome;
    private TextInputEditText etReport;
    private Uri photoUri;
    private Uri cameraUri;

    private final ActivityResultLauncher<String[]> locationPermission = registerForActivityResult(
            new ActivityResultContracts.RequestMultiplePermissions(), r -> launchCamera());

    private final ActivityResultLauncher<Uri> takePhoto = registerForActivityResult(
            new ActivityResultContracts.TakePicture(), ok -> {
                if (Boolean.TRUE.equals(ok)) setPhoto(cameraUri);
            });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_verification);
        id = getIntent().getStringExtra(EXTRA_ID);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        tvStatus = findViewById(R.id.tvStatus);
        tvClaim = findViewById(R.id.tvClaim);
        tvDetails = findViewById(R.id.tvDetails);
        tvPlace = findViewById(R.id.tvPlace);
        tvPeople = findViewById(R.id.tvPeople);
        tvOutcome = findViewById(R.id.tvOutcome);
        tvConsensus = findViewById(R.id.tvConsensus);
        layoutReports = findViewById(R.id.layoutReports);
        tvPrivacy = findViewById(R.id.tvPrivacy);
        map = findViewById(R.id.map);
        ivReportPhoto = findViewById(R.id.ivReportPhoto);
        layoutRecipientActions = findViewById(R.id.layoutRecipientActions);
        layoutVerifierActions = findViewById(R.id.layoutVerifierActions);
        layoutReportForm = findViewById(R.id.layoutReportForm);
        layoutResult = findViewById(R.id.layoutResult);
        btnCancel = findViewById(R.id.btnCancel);
        btnOpenAnalysis = findViewById(R.id.btnOpenAnalysis);
        btnSendReport = findViewById(R.id.btnSendReport);
        rgOutcome = findViewById(R.id.rgOutcome);
        etReport = findViewById(R.id.etReport);

        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        map.getController().setZoom(16.0);

        findViewById(R.id.btnAccept).setOnClickListener(v -> confirmAccept());
        findViewById(R.id.btnDecline).setOnClickListener(v -> decline());
        findViewById(R.id.btnNavigate).setOnClickListener(v -> navigate());
        findViewById(R.id.btnRelease).setOnClickListener(v -> confirm(R.string.verif_release_confirm, this::release));
        findViewById(R.id.btnDispute).setOnClickListener(v -> confirm(R.string.verif_dispute_confirm, this::dispute));
        findViewById(R.id.btnTakePhoto).setOnClickListener(v -> openCamera());
        btnSendReport.setOnClickListener(v -> sendReport());
        btnCancel.setOnClickListener(v -> confirm(R.string.verif_cancel_confirm, this::cancelRequest));
        btnOpenAnalysis.setOnClickListener(v -> {
            if (current != null && current.analysis_id != null) {
                startActivity(ResultActivity.intent(this, current.analysis_id));
            }
        });
        load();
    }

    private void load() {
        ApiClient.getApiService().getVerification(id).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                bind(body);
            }

            @Override
            public void onError(int code, String message) {
                // Demande prise par quelqu'un d'autre, annulée ou expirée : elle n'est plus visible.
                VerificationNotifier.dismiss(VerificationActivity.this, id);
                Toast.makeText(VerificationActivity.this, message, Toast.LENGTH_LONG).show();
                finish();
            }
        });
    }

    private void bind(Verification v) {
        current = v;
        boolean completed = "completed".equals(v.status);
        tvStatus.setText(Format.verificationStatus(this, v.status));
        tvStatus.setTextColor(getColor("open".equals(v.status) || "accepted".equals(v.status)
                ? R.color.primary : R.color.gray_text));
        tvClaim.setText(v.claim);
        tvDetails.setText(v.details);
        tvDetails.setVisibility(v.details == null || v.details.isEmpty() ? View.GONE : View.VISIBLE);
        tvPlace.setText(getString(R.string.verif_place_line, v.place_label,
                String.format(Locale.getDefault(), "%.5f, %.5f", v.latitude, v.longitude)));

        StringBuilder people = new StringBuilder(getString(R.string.verif_asked_by, v.requester_name));
        if (v.requester_organization != null && !v.requester_organization.isEmpty()) {
            people.append(" (").append(v.requester_organization).append(")");
        }
        people.append(" · ").append(Format.date(v.created_at));
        if (v.verifier_name != null) people.append("\n").append(getString(R.string.verif_by, v.verifier_name));
        if ("open".equals(v.status)) people.append("\n").append(getString(R.string.verif_expires, Format.date(v.expires_at)));
        tvPeople.setText(people);

        GeoPoint point = new GeoPoint(v.latitude, v.longitude);
        map.getOverlays().clear();
        Marker marker = new Marker(map);
        marker.setPosition(point);
        marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        marker.setTitle(v.place_label);
        map.getOverlays().add(marker);
        map.getController().setCenter(point);
        map.invalidate();

        boolean recipientOpen = "recipient".equals(v.role) && "open".equals(v.status);
        boolean verifierActive = "verifier".equals(v.role) && "accepted".equals(v.status);
        boolean requester = "requester".equals(v.role);
        layoutRecipientActions.setVisibility(recipientOpen ? View.VISIBLE : View.GONE);
        tvPrivacy.setVisibility(recipientOpen ? View.VISIBLE : View.GONE);
        layoutVerifierActions.setVisibility(verifierActive ? View.VISIBLE : View.GONE);
        layoutReportForm.setVisibility(verifierActive ? View.VISIBLE : View.GONE);
        btnCancel.setVisibility(requester && ("open".equals(v.status) || "accepted".equals(v.status))
                ? View.VISIBLE : View.GONE);
        btnOpenAnalysis.setVisibility(requester && v.analysis_id != null ? View.VISIBLE : View.GONE);

        layoutResult.setVisibility(completed ? View.VISIBLE : View.GONE);
        if (completed) {
            tvOutcome.setText(Format.outcome(this, v.outcome));
            tvOutcome.setTextColor(getColor(Format.verdictColor(v.outcome)));
            tvConsensus.setText("agreed".equals(v.consensus) ? R.string.verif_consensus_agreed
                    : "divergent".equals(v.consensus) ? R.string.verif_consensus_divergent : R.string.verif_consensus_single);
        }
        findViewById(R.id.btnDispute).setVisibility(completed && requester && "single".equals(v.consensus)
                ? View.VISIBLE : View.GONE);
        renderReports(v);
        if (v.required_reports > 1 && !completed && requester) {
            tvPeople.append("\n" + getString(R.string.verif_second_pending));
        }
    }

    private void confirm(int message, Runnable action) {
        new AlertDialog.Builder(this).setMessage(message)
                .setPositiveButton(R.string.confirm, (d, w) -> action.run())
                .setNegativeButton(R.string.cancel, null).show();
    }

    private void confirmAccept() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.verif_accept_title)
                .setMessage(R.string.verif_accept_message)
                .setPositiveButton(R.string.verif_accept, (d, w) -> accept())
                .setNegativeButton(R.string.cancel, null).show();
    }

    private void accept() {
        ApiClient.getApiService().acceptVerification(id).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                Toast.makeText(VerificationActivity.this, R.string.verif_accepted_toast, Toast.LENGTH_LONG).show();
                bind(body);
            }

            @Override
            public void onError(int code, String message) {
                super.onError(code, message);
                if (code == 409 || code == 404) finish();  // quelqu'un d'autre a été plus rapide
            }
        });
    }

    private void decline() {
        ApiClient.getApiService().declineVerification(id).enqueue(new ApiCallback<Void>(this) {
            @Override
            public void onSuccess(Void body) {
                VerificationNotifier.dismiss(VerificationActivity.this, id);
                finish();
            }
        });
    }

    private void release() {
        ApiClient.getApiService().releaseVerification(id).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                finish();
            }
        });
    }

    private void cancelRequest() {
        ApiClient.getApiService().cancelVerification(id).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                bind(body);
            }
        });
    }

    private void navigate() {
        if (current == null) return;
        Uri uri = Uri.parse(String.format(Locale.US, "geo:%f,%f?q=%f,%f(%s)", current.latitude, current.longitude,
                current.latitude, current.longitude, Uri.encode(current.place_label)));
        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        if (intent.resolveActivity(getPackageManager()) == null) {
            intent = new Intent(Intent.ACTION_VIEW, Uri.parse(String.format(Locale.US,
                    "https://www.openstreetmap.org/?mlat=%f&mlon=%f#map=18/%f/%f",
                    current.latitude, current.longitude, current.latitude, current.longitude)));
        }
        startActivity(intent);
    }

    /** Constats certifiés : chaque contrôle est affiché, réussi ou non, avec l'empreinte de la photo. */
    private void renderReports(Verification v) {
        layoutReports.removeAllViews();
        if (v.reports == null) return;
        for (Verification.Report r : v.reports) {
            View row = getLayoutInflater().inflate(R.layout.item_report, layoutReports, false);
            ((TextView) row.findViewById(R.id.tvWho)).setText(getString(R.string.verif_report_by, r.verifier_name,
                    Format.date(r.received_at)));
            TextView outcome = row.findViewById(R.id.tvOutcome);
            outcome.setText(Format.outcome(this, r.outcome));
            Format.stamp(outcome, Format.verdictColor(r.outcome));
            String checks = check(r.photo_sha256 != null && r.capture_verified, getString(R.string.verif_check_capture),
                    getString(r.photo_sha256 == null ? R.string.verif_check_no_photo : R.string.verif_check_capture_ko))
                    + "\n" + check(r.on_site, getString(R.string.verif_check_on_site, distance(r.distance_bucket)),
                    getString(r.mock_location ? R.string.verif_check_mock : R.string.verif_check_off_site, distance(r.distance_bucket)))
                    + "\n" + check(r.certified, getString(R.string.verif_check_signed), getString(R.string.verif_check_unsigned));
            ((TextView) row.findViewById(R.id.tvChecks)).setText(checks);
            TextView text = row.findViewById(R.id.tvText);
            text.setText(r.report == null || r.report.isEmpty() ? getString(R.string.verif_no_report) : r.report);
            ImageLoader.load(row.findViewById(R.id.ivPhoto), r.photo_url);
            TextView hash = row.findViewById(R.id.tvHash);
            hash.setVisibility(r.photo_sha256 == null ? View.GONE : View.VISIBLE);
            if (r.photo_sha256 != null) hash.setText(getString(R.string.verif_hash, r.photo_sha256.substring(0, 16)));
            layoutReports.addView(row);
        }
    }

    private static String check(boolean ok, String yes, String no) {
        return ok ? "✓ " + yes : "✗ " + no;
    }

    private String distance(String bucket) {
        if (bucket == null || "inconnue".equals(bucket)) return getString(R.string.verif_distance_unknown);
        if (bucket.startsWith(">")) return getString(R.string.verif_distance_far);
        return getString(R.string.verif_distance_under, bucket.substring(1));
    }

    private void dispute() {
        ApiClient.getApiService().disputeVerification(id).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                Toast.makeText(VerificationActivity.this, R.string.verif_dispute_sent, Toast.LENGTH_LONG).show();
                bind(body);
            }
        });
    }

    /** Capture verrouillée : la position sert au contrôle de présence, puis le jeton est demandé au serveur. */
    private void openCamera() {
        if (!LocationReporter.hasPermission(this)) {
            locationPermission.launch(new String[]{android.Manifest.permission.ACCESS_FINE_LOCATION,
                    android.Manifest.permission.ACCESS_COARSE_LOCATION});
            return;
        }
        launchCamera();
    }

    private void launchCamera() {
        ApiClient.getApiService().captureToken(id).enqueue(new ApiCallback<JsonObject>(this) {
            @Override
            public void onSuccess(JsonObject body) {
                captureToken = body.get("token").getAsString();
                File file = new File(getCacheDir(), "constat-" + System.currentTimeMillis() + ".jpg");
                cameraUri = FileProvider.getUriForFile(VerificationActivity.this, getPackageName() + ".files", file);
                takePhoto.launch(cameraUri);
            }
        });
    }

    private void setPhoto(Uri uri) {
        photoUri = uri;
        ivReportPhoto.setVisibility(View.VISIBLE);
        ivReportPhoto.setImageURI(uri);
    }

    private void sendReport() {
        int checked = rgOutcome.getCheckedRadioButtonId();
        String outcome = checked == R.id.rbCorrect ? "correct" : checked == R.id.rbIncorrect ? "incorrect"
                : checked == R.id.rbUndetermined ? "indetermine" : null;
        if (outcome == null) {
            Toast.makeText(this, R.string.verif_outcome_required, Toast.LENGTH_LONG).show();
            return;
        }
        MultipartBody.Part photo = null;
        if (photoUri != null) {
            try {
                photo = FileParts.part(this, "photo", photoUri);
            } catch (Exception e) {
                Toast.makeText(this, R.string.error_file, Toast.LENGTH_LONG).show();
                return;
            }
        }
        String report = etReport.getText() != null ? etReport.getText().toString().trim() : "";
        MultipartBody.Part photoPart = photo;
        btnSendReport.setEnabled(false);
        // Position au moment du constat : le serveur n'en garde que la tranche de distance au lieu.
        LocationReporter.current(this, location -> {
            Map<String, RequestBody> fields = new HashMap<>();
            fields.put("outcome", FileParts.text(outcome));
            fields.put("report", FileParts.text(report));
            fields.put("device_time", FileParts.text(OffsetDateTime.now().toString()));
            if (captureToken != null && photoPart != null) fields.put("capture_token", FileParts.text(captureToken));
            if (location != null) {
                fields.put("latitude", FileParts.text(String.valueOf(location.getLatitude())));
                fields.put("longitude", FileParts.text(String.valueOf(location.getLongitude())));
                fields.put("accuracy", FileParts.text(String.valueOf(location.getAccuracy())));
                boolean mock = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ? location.isMock() : location.isFromMockProvider();
                fields.put("mock_location", FileParts.text(String.valueOf(mock)));
            }
            ApiClient.getApiService().reportVerification(id, fields, photoPart).enqueue(new ApiCallback<Verification>(this) {
                @Override
                public void onSuccess(Verification body) {
                    captureToken = null;
                    Toast.makeText(VerificationActivity.this, "open".equals(body.status)
                            ? R.string.verif_report_second : R.string.verif_report_sent, Toast.LENGTH_LONG).show();
                    bind(body);
                }

                @Override
                public void onFinally() {
                    btnSendReport.setEnabled(true);
                }
            });
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        map.onResume();
    }

    @Override
    protected void onPause() {
        map.onPause();
        super.onPause();
    }
}
