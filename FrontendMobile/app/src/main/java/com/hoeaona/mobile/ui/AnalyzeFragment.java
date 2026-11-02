package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisOut;
import okhttp3.MediaType;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.ArrayList;

public class AnalyzeFragment extends Fragment {
    private TextInputEditText etAnalysisText, etAnalysisUrl;
    private MaterialButton btnSubmitAnalysis;
    private LinearLayout layoutResult;
    private TextView tvResultTitle, tvResultVerdict, tvResultSummary;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_analyze, container, false);
        etAnalysisText = view.findViewById(R.id.etAnalysisText);
        etAnalysisUrl = view.findViewById(R.id.etAnalysisUrl);
        btnSubmitAnalysis = view.findViewById(R.id.btnSubmitAnalysis);
        layoutResult = view.findViewById(R.id.layoutResult);
        tvResultTitle = view.findViewById(R.id.tvResultTitle);
        tvResultVerdict = view.findViewById(R.id.tvResultVerdict);
        tvResultSummary = view.findViewById(R.id.tvResultSummary);

        btnSubmitAnalysis.setOnClickListener(v -> submitAnalysis());

        return view;
    }

    private void submitAnalysis() {
        String text = etAnalysisText.getText() != null ? etAnalysisText.getText().toString().trim() : "";
        String url = etAnalysisUrl.getText() != null ? etAnalysisUrl.getText().toString().trim() : "";

        if (text.isEmpty()) {
            Toast.makeText(getContext(), "Veuillez entrer un texte à analyser", Toast.LENGTH_SHORT).show();
            return;
        }

        btnSubmitAnalysis.setEnabled(false);
        btnSubmitAnalysis.setText("Analyse en cours...");

        RequestBody textBody = RequestBody.create(MediaType.parse("text/plain"), text);
        org.json.JSONArray jsonUrls = new org.json.JSONArray();
        if (!url.isEmpty()) jsonUrls.put(url);
        RequestBody urlsBody = RequestBody.create(MediaType.parse("text/plain"), jsonUrls.toString());

        ApiClient.getApiService().createAnalysis(textBody, urlsBody, new ArrayList<>()).enqueue(new Callback<AnalysisOut>() {
            @Override
            public void onResponse(Call<AnalysisOut> call, Response<AnalysisOut> response) {
                btnSubmitAnalysis.setEnabled(true);
                btnSubmitAnalysis.setText("Lancer l'analyse");
                if (response.isSuccessful() && response.body() != null) {
                    AnalysisOut analysis = response.body();
                    layoutResult.setVisibility(View.VISIBLE);
                    tvResultTitle.setText(analysis.getTitle());
                    tvResultVerdict.setText("Verdict : " + (analysis.getVerdict() != null ? analysis.getVerdict() : analysis.getStatus()));
                    tvResultSummary.setText(analysis.getNotes() != null ? analysis.getNotes() : "Analyse effectuée avec succès.");
                    Toast.makeText(getContext(), "Analyse terminée !", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(getContext(), "Erreur lors de l'analyse", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<AnalysisOut> call, Throwable t) {
                btnSubmitAnalysis.setEnabled(true);
                btnSubmitAnalysis.setText("Lancer l'analyse");
                Toast.makeText(getContext(), "Erreur réseau : " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }
}
