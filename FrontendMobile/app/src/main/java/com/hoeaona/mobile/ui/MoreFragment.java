package com.hoeaona.mobile.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.fragment.app.Fragment;
import com.hoeaona.mobile.HoeApp;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.auth.LoginActivity;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.verify.LocationReporter;

/** Menu « Plus » : profil, notifications, annuaire, statistiques, paramètres, administration, déconnexion. */
public class MoreFragment extends Fragment {
    private User me;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_more, container, false);
        TextView tvName = view.findViewById(R.id.tvName);
        TextView tvEmail = view.findViewById(R.id.tvEmail);
        View admin = view.findViewById(R.id.itemAdmin);

        ApiClient.getApiService().getMe().enqueue(new ApiCallback<User>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(User body) {
                me = body;
                tvName.setText(body.display_name);
                tvEmail.setText(body.email + (body.organization == null || body.organization.isEmpty() ? "" : " · " + body.organization));
                admin.setVisibility(body.isAdmin() ? View.VISIBLE : View.GONE);
            }
        });

        view.findViewById(R.id.itemProfile).setOnClickListener(v -> {
            if (me != null) startActivity(new Intent(requireContext(), ProfileActivity.class).putExtra(ProfileActivity.EXTRA_ID, me.id));
        });
        view.findViewById(R.id.itemNotifications).setOnClickListener(v ->
                startActivity(HostActivity.intent(requireContext(), HostActivity.NOTIFICATIONS)));
        view.findViewById(R.id.itemSources).setOnClickListener(v ->
                startActivity(HostActivity.intent(requireContext(), HostActivity.SOURCES)));
        view.findViewById(R.id.itemStats).setOnClickListener(v ->
                startActivity(HostActivity.intent(requireContext(), HostActivity.STATS)));
        view.findViewById(R.id.itemSettings).setOnClickListener(v ->
                startActivity(HostActivity.intent(requireContext(), HostActivity.SETTINGS)));
        admin.setOnClickListener(v -> startActivity(HostActivity.intent(requireContext(), HostActivity.ADMIN)));
        view.findViewById(R.id.itemLogout).setOnClickListener(v -> new AlertDialog.Builder(requireContext())
                .setMessage(R.string.logout_confirm)
                .setPositiveButton(R.string.logout, (d, w) -> logout())
                .setNegativeButton(R.string.cancel, null).show());
        return view;
    }

    /** La déconnexion efface aussi la position côté serveur : plus aucune demande n'arrive. */
    private void logout() {
        LocationReporter.setEnabled(requireContext(), false);
        ApiClient.getApiService().logout().enqueue(new ApiCallback<Void>(null) {
            @Override
            public void onSuccess(Void body) {}

            @Override
            public void onError(int code, String message) {}

            @Override
            public void onFinally() {
                // Après la réponse : sinon l'écran de connexion trouverait encore la session ouverte.
                ApiClient.clearSession();
                HoeApp.get().startActivity(new Intent(HoeApp.get(), LoginActivity.class)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK));
            }
        });
    }
}
