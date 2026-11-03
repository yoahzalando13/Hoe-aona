package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.button.MaterialButtonToggleGroup;
import com.google.android.material.materialswitch.MaterialSwitch;
import com.google.android.material.slider.Slider;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Health;
import com.hoeaona.mobile.model.Preferences;
import com.hoeaona.mobile.util.Lang;

/** Langue, préférences d'analyse du compte et état des services du backend. */
public class SettingsFragment extends Fragment {
    private MaterialButtonToggleGroup langGroup, reportLangGroup;
    private Slider slWeightSource, slWeightVeracity, slWeightAi, slAiThreshold, slMinReliability;
    private MaterialSwitch swDeepAi;
    private TextInputEditText etCountry, etRetention;
    private MaterialButton btnSave;
    private TextView tvServices, tvServer;
    private Preferences prefs;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_settings, container, false);
        langGroup = view.findViewById(R.id.langGroup);
        reportLangGroup = view.findViewById(R.id.reportLangGroup);
        slWeightSource = view.findViewById(R.id.slWeightSource);
        slWeightVeracity = view.findViewById(R.id.slWeightVeracity);
        slWeightAi = view.findViewById(R.id.slWeightAi);
        slAiThreshold = view.findViewById(R.id.slAiThreshold);
        slMinReliability = view.findViewById(R.id.slMinReliability);
        swDeepAi = view.findViewById(R.id.swDeepAi);
        etCountry = view.findViewById(R.id.etCountry);
        etRetention = view.findViewById(R.id.etRetention);
        btnSave = view.findViewById(R.id.btnSave);
        tvServices = view.findViewById(R.id.tvServices);
        tvServer = view.findViewById(R.id.tvServer);

        tvServer.setText(getString(R.string.settings_server, ApiClient.getServerUrl()));
        String lang = Lang.current();
        langGroup.check(idForLang(lang, R.id.btnLangMg, R.id.btnLangFr, R.id.btnLangEn));
        langGroup.addOnButtonCheckedListener((g, checkedId, checked) -> {
            if (!checked) return;
            String code = langFor(checkedId, R.id.btnLangMg, R.id.btnLangEn);
            if (prefs != null) {
                prefs.ui_language = code;
                ApiClient.getApiService().saveSettings(prefs).enqueue(silent());
            }
            Lang.set(code);
        });
        btnSave.setOnClickListener(v -> save());
        btnSave.setEnabled(false);
        load();
        return view;
    }

    private static int idForLang(String lang, int mg, int fr, int en) {
        return "mg".equals(lang) ? mg : "en".equals(lang) ? en : fr;
    }

    private static String langFor(int id, int mg, int en) {
        return id == mg ? "mg" : id == en ? "en" : "fr";
    }

    /** Curseurs en entiers (pourcentages) : une valeur hors pas ferait planter le Slider. */
    private static float clamp(double value, int min, int max, int step) {
        long v = Math.round(Math.max(min, Math.min(max, value)) / step) * step;
        return (float) v;
    }

    private void load() {
        ApiClient.getApiService().getSettings().enqueue(new ApiCallback<Preferences>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(Preferences body) {
                prefs = body;
                slWeightSource.setValue(clamp(body.weight_source, 0, 100, 5));
                slWeightVeracity.setValue(clamp(body.weight_veracity, 0, 100, 5));
                slWeightAi.setValue(clamp(body.weight_ai, 0, 100, 5));
                slAiThreshold.setValue(clamp(body.ai_exclusion_threshold * 100, 50, 95, 5));
                slMinReliability.setValue(clamp(body.min_source_reliability * 100, 0, 90, 5));
                swDeepAi.setChecked(body.deep_ai_detection);
                etCountry.setText(body.default_country);
                etRetention.setText(String.valueOf(body.history_retention_days));
                reportLangGroup.check(idForLang(body.report_language, R.id.btnReportMg, R.id.btnReportFr, R.id.btnReportEn));
                btnSave.setEnabled(true);
            }
        });
        ApiClient.getApiService().health().enqueue(new ApiCallback<Health>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(Health body) {
                StringBuilder text = new StringBuilder();
                for (Health.Provider p : body.providers) {
                    text.append(p.configured ? "✓ " : "✗ ").append(p.label).append(" — ").append(p.role).append('\n');
                }
                text.append(getString(R.string.settings_mcp, body.mcp_mode, body.mcp_tools == null ? 0 : body.mcp_tools.size()));
                tvServices.setText(text.toString());
            }
        });
    }

    private void save() {
        if (prefs == null) return;
        prefs.weight_source = Math.round(slWeightSource.getValue());
        prefs.weight_veracity = Math.round(slWeightVeracity.getValue());
        prefs.weight_ai = Math.round(slWeightAi.getValue());
        prefs.ai_exclusion_threshold = Math.round(slAiThreshold.getValue()) / 100.0;
        prefs.min_source_reliability = Math.round(slMinReliability.getValue()) / 100.0;
        prefs.deep_ai_detection = swDeepAi.isChecked();
        prefs.default_country = etCountry.getText() != null ? etCountry.getText().toString().trim().toUpperCase(java.util.Locale.ROOT) : "MDG";
        try {
            prefs.history_retention_days = Integer.parseInt(etRetention.getText() != null ? etRetention.getText().toString().trim() : "90");
        } catch (NumberFormatException e) {
            etRetention.setError(getString(R.string.settings_retention_invalid));
            return;
        }
        prefs.report_language = langFor(reportLangGroup.getCheckedButtonId(), R.id.btnReportMg, R.id.btnReportEn);
        prefs.ui_language = Lang.current();
        btnSave.setEnabled(false);
        ApiClient.getApiService().saveSettings(prefs).enqueue(new ApiCallback<Preferences>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(Preferences body) {
                prefs = body;
                Toast.makeText(requireContext(), R.string.saved, Toast.LENGTH_SHORT).show();
            }

            @Override
            public void onFinally() {
                btnSave.setEnabled(true);
            }
        });
    }

    private ApiCallback<Preferences> silent() {
        return new ApiCallback<Preferences>(null) {
            @Override public void onSuccess(Preferences body) {}
            @Override public void onError(int code, String message) {}
        };
    }
}
