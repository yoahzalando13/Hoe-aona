package com.hoeaona.mobile.verify;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Verification;
import org.osmdroid.events.MapEventsReceiver;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.MapEventsOverlay;
import org.osmdroid.views.overlay.Marker;

import java.util.Locale;

/** Nouvelle demande : affirmation à constater et lieu précis, choisi sur la carte. */
public class CreateVerificationActivity extends AppCompatActivity {
    public static final String EXTRA_CLAIM = "claim";
    public static final String EXTRA_ANALYSIS_ID = "analysis_id";
    private static final GeoPoint ANTANANARIVO = new GeoPoint(-18.8792, 47.5079);

    private TextInputEditText etClaim, etDetails, etPlace;
    private TextView tvCoordinates;
    private MaterialButton btnSubmit;
    private MapView map;
    private Marker marker;
    private GeoPoint selected;
    private String analysisId;

    private final ActivityResultLauncher<String[]> locationPermission = registerForActivityResult(
            new ActivityResultContracts.RequestMultiplePermissions(), r -> useMyPosition());

    public static Intent forClaim(Context context, String claim, String analysisId) {
        return new Intent(context, CreateVerificationActivity.class)
                .putExtra(EXTRA_CLAIM, claim).putExtra(EXTRA_ANALYSIS_ID, analysisId);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_create_verification);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        etClaim = findViewById(R.id.etClaim);
        etDetails = findViewById(R.id.etDetails);
        etPlace = findViewById(R.id.etPlace);
        tvCoordinates = findViewById(R.id.tvCoordinates);
        btnSubmit = findViewById(R.id.btnSubmit);
        map = findViewById(R.id.map);

        etClaim.setText(getIntent().getStringExtra(EXTRA_CLAIM));
        analysisId = getIntent().getStringExtra(EXTRA_ANALYSIS_ID);
        TextView tvLinked = findViewById(R.id.tvLinkedAnalysis);
        tvLinked.setVisibility(analysisId != null ? View.VISIBLE : View.GONE);

        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        map.getController().setZoom(14.0);
        map.getController().setCenter(ANTANANARIVO);
        map.getOverlays().add(new MapEventsOverlay(new MapEventsReceiver() {
            @Override
            public boolean singleTapConfirmedHelper(GeoPoint p) {
                select(p);
                return true;
            }

            @Override
            public boolean longPressHelper(GeoPoint p) {
                select(p);
                return true;
            }
        }));
        // La carte capte les gestes : le défilement de la page ne doit pas les lui voler.
        map.setOnTouchListener((v, e) -> {
            v.getParent().requestDisallowInterceptTouchEvent(true);
            return false;
        });

        findViewById(R.id.btnMyPosition).setOnClickListener(v -> {
            if (LocationReporter.hasPermission(this)) useMyPosition();
            else locationPermission.launch(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION});
        });
        btnSubmit.setOnClickListener(v -> submit());
    }

    private void useMyPosition() {
        if (!LocationReporter.hasPermission(this)) {
            Toast.makeText(this, R.string.verif_permission_denied, Toast.LENGTH_LONG).show();
            return;
        }
        LocationReporter.current(this, location -> {
            if (location == null) {
                Toast.makeText(this, R.string.verif_no_position, Toast.LENGTH_LONG).show();
                return;
            }
            GeoPoint p = new GeoPoint(location.getLatitude(), location.getLongitude());
            map.getController().animateTo(p, 17.0, 600L);
            select(p);
        });
    }

    private void select(GeoPoint p) {
        selected = p;
        if (marker == null) {
            marker = new Marker(map);
            marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
            marker.setDraggable(true);
            marker.setOnMarkerDragListener(new Marker.OnMarkerDragListener() {
                @Override public void onMarkerDrag(Marker m) {}
                @Override public void onMarkerDragEnd(Marker m) { select(m.getPosition()); }
                @Override public void onMarkerDragStart(Marker m) {}
            });
            map.getOverlays().add(marker);
        }
        marker.setPosition(p);
        map.invalidate();
        tvCoordinates.setText(String.format(Locale.US, "%.5f, %.5f", p.getLatitude(), p.getLongitude()));
    }

    private String text(TextInputEditText field) {
        return field.getText() != null ? field.getText().toString().trim() : "";
    }

    private void submit() {
        String claim = text(etClaim), place = text(etPlace);
        if (claim.length() < 5) {
            etClaim.setError(getString(R.string.verif_claim_required));
            return;
        }
        if (place.length() < 2) {
            etPlace.setError(getString(R.string.verif_place_required));
            return;
        }
        if (selected == null) {
            Toast.makeText(this, R.string.verif_point_required, Toast.LENGTH_LONG).show();
            return;
        }
        JsonObject payload = new JsonObject();
        payload.addProperty("claim", claim);
        payload.addProperty("details", text(etDetails));
        payload.addProperty("place_label", place);
        payload.addProperty("latitude", selected.getLatitude());
        payload.addProperty("longitude", selected.getLongitude());
        if (analysisId != null) payload.addProperty("analysis_id", analysisId);

        btnSubmit.setEnabled(false);
        ApiClient.getApiService().createVerification(payload).enqueue(new ApiCallback<Verification>(this) {
            @Override
            public void onSuccess(Verification body) {
                Toast.makeText(CreateVerificationActivity.this, R.string.verif_sent, Toast.LENGTH_LONG).show();
                startActivity(new Intent(CreateVerificationActivity.this, VerificationActivity.class)
                        .putExtra(VerificationActivity.EXTRA_ID, body.id));
                finish();
            }

            @Override
            public void onFinally() {
                btnSubmit.setEnabled(true);
            }
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
