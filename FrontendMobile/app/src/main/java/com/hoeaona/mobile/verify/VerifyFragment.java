package com.hoeaona.mobile.verify;

import android.Manifest;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton;
import com.google.android.material.materialswitch.MaterialSwitch;
import com.google.android.material.tabs.TabLayout;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Verification;
import com.hoeaona.mobile.util.Format;
import retrofit2.Call;

import java.util.List;

/** Vérification physique : demandes reçues à proximité, demandes envoyées, vérifications acceptées. */
public class VerifyFragment extends Fragment {
    private static final int TAB_NEARBY = 0, TAB_MINE = 1, TAB_ASSIGNED = 2;

    private MaterialSwitch switchSharing;
    private TextView tvSharingStatus, tvEmpty;
    private MaterialButton btnBackground;
    private TabLayout tabs;
    private SwipeRefreshLayout swipe;
    private VerificationAdapter adapter;

    private final ActivityResultLauncher<String[]> locationPermission = registerForActivityResult(
            new ActivityResultContracts.RequestMultiplePermissions(), result -> {
                if (LocationReporter.hasPermission(requireContext())) {
                    enableSharing();
                } else {
                    switchSharing.setChecked(false);
                    tvSharingStatus.setText(R.string.verif_permission_denied);
                }
            });

    private final ActivityResultLauncher<String> backgroundPermission = registerForActivityResult(
            new ActivityResultContracts.RequestPermission(), granted -> refreshSharingUi());

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_verify, container, false);
        switchSharing = view.findViewById(R.id.switchSharing);
        tvSharingStatus = view.findViewById(R.id.tvSharingStatus);
        btnBackground = view.findViewById(R.id.btnBackground);
        tvEmpty = view.findViewById(R.id.tvEmpty);
        tabs = view.findViewById(R.id.tabs);
        swipe = view.findViewById(R.id.swipeRefresh);
        RecyclerView recycler = view.findViewById(R.id.recyclerView);
        ExtendedFloatingActionButton fab = view.findViewById(R.id.fabNewRequest);

        adapter = new VerificationAdapter(v -> startActivity(new Intent(requireContext(), VerificationActivity.class)
                .putExtra(VerificationActivity.EXTRA_ID, v.id)));
        recycler.setLayoutManager(new LinearLayoutManager(requireContext()));
        recycler.setAdapter(adapter);

        tabs.addTab(tabs.newTab().setText(R.string.verif_tab_nearby));
        tabs.addTab(tabs.newTab().setText(R.string.verif_tab_mine));
        tabs.addTab(tabs.newTab().setText(R.string.verif_tab_assigned));
        tabs.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override public void onTabSelected(TabLayout.Tab tab) { load(); }
            @Override public void onTabUnselected(TabLayout.Tab tab) {}
            @Override public void onTabReselected(TabLayout.Tab tab) { load(); }
        });

        switchSharing.setOnClickListener(v -> {
            if (switchSharing.isChecked()) askConsent();
            else {
                LocationReporter.stopSharing(requireContext());
                refreshSharingUi();
            }
        });
        btnBackground.setOnClickListener(v -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                backgroundPermission.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION);
            }
        });
        swipe.setOnRefreshListener(this::load);
        fab.setOnClickListener(v -> startActivity(new Intent(requireContext(), CreateVerificationActivity.class)));
        return view;
    }

    @Override
    public void onResume() {
        super.onResume();
        refreshSharingUi();
        load();
    }

    /** Consentement explicite avant tout envoi de position. */
    private void askConsent() {
        new AlertDialog.Builder(requireContext())
                .setTitle(R.string.verif_consent_title)
                .setMessage(R.string.verif_consent_message)
                .setPositiveButton(R.string.verif_consent_accept, (d, w) -> {
                    if (LocationReporter.hasPermission(requireContext())) enableSharing();
                    else locationPermission.launch(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION});
                })
                .setNegativeButton(R.string.cancel, (d, w) -> switchSharing.setChecked(false))
                .setOnCancelListener(d -> switchSharing.setChecked(false))
                .show();
    }

    private void enableSharing() {
        LocationReporter.setEnabled(requireContext(), true);
        LocationReporter.reportAsync(requireContext());
        refreshSharingUi();
    }

    private void refreshSharingUi() {
        boolean enabled = LocationReporter.isEnabled(requireContext()) && LocationReporter.hasPermission(requireContext());
        switchSharing.setChecked(enabled);
        btnBackground.setVisibility(enabled && !LocationReporter.hasBackgroundPermission(requireContext())
                ? View.VISIBLE : View.GONE);
        if (!enabled) {
            tvSharingStatus.setText(R.string.verif_sharing_off);
            return;
        }
        ApiClient.getApiService().locationStatus().enqueue(new ApiCallback<JsonObject>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(JsonObject body) {
                boolean sharing = body != null && body.get("sharing").getAsBoolean();
                tvSharingStatus.setText(sharing
                        ? getString(R.string.verif_sharing_on, Format.date(body.get("updated_at").getAsString()))
                        : getString(R.string.verif_sharing_pending));
            }

            @Override
            public void onError(int code, String message) {
                tvSharingStatus.setText(message);
            }
        });
    }

    private void load() {
        if (getView() == null) return;
        swipe.setRefreshing(true);
        int tab = tabs.getSelectedTabPosition();
        Call<List<Verification>> call = tab == TAB_MINE ? ApiClient.getApiService().myVerifications()
                : tab == TAB_ASSIGNED ? ApiClient.getApiService().assignedVerifications()
                : ApiClient.getApiService().nearbyVerifications();
        call.enqueue(new ApiCallback<List<Verification>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<Verification> body) {
                adapter.setItems(body);
                boolean empty = body == null || body.isEmpty();
                tvEmpty.setVisibility(empty ? View.VISIBLE : View.GONE);
                tvEmpty.setText(tab == TAB_MINE ? R.string.verif_empty_mine
                        : tab == TAB_ASSIGNED ? R.string.verif_empty_assigned : R.string.verif_empty_nearby);
            }

            @Override
            public void onError(int code, String message) {
                adapter.setItems(null);
                tvEmpty.setVisibility(View.VISIBLE);
                tvEmpty.setText(message);
            }

            @Override
            public void onFinally() {
                swipe.setRefreshing(false);
            }
        });
    }
}
