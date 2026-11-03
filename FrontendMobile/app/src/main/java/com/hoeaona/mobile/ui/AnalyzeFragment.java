package com.hoeaona.mobile.ui;

import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.chip.Chip;
import com.google.android.material.chip.ChipGroup;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisOut;
import com.hoeaona.mobile.util.FileParts;
import okhttp3.MultipartBody;
import org.json.JSONArray;

import java.util.ArrayList;
import java.util.List;

/** Texte, liens et fichiers (image, document, audio : 6 au plus) envoyés pour analyse. */
public class AnalyzeFragment extends Fragment {
    private static final int MAX_FILES = 6;
    private static final String[] MIME_TYPES = {"image/*", "audio/*", "video/webm", "application/pdf", "text/*",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"};

    private TextInputEditText etAnalysisText, etAnalysisUrl;
    private MaterialButton btnSubmitAnalysis;
    private ChipGroup chipFiles;
    private final List<Uri> files = new ArrayList<>();

    private final ActivityResultLauncher<String[]> pickFiles = registerForActivityResult(
            new ActivityResultContracts.OpenMultipleDocuments(), uris -> {
                for (Uri uri : uris) {
                    if (files.size() >= MAX_FILES) {
                        Toast.makeText(requireContext(), R.string.analyze_max_files, Toast.LENGTH_LONG).show();
                        break;
                    }
                    if (!files.contains(uri)) files.add(uri);
                }
                renderFiles();
            });

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_analyze, container, false);
        etAnalysisText = view.findViewById(R.id.etAnalysisText);
        etAnalysisUrl = view.findViewById(R.id.etAnalysisUrl);
        btnSubmitAnalysis = view.findViewById(R.id.btnSubmitAnalysis);
        chipFiles = view.findViewById(R.id.chipFiles);

        view.findViewById(R.id.btnAddFiles).setOnClickListener(v -> pickFiles.launch(MIME_TYPES));
        btnSubmitAnalysis.setOnClickListener(v -> submitAnalysis());
        renderFiles();
        return view;
    }

    private void renderFiles() {
        chipFiles.removeAllViews();
        for (Uri uri : new ArrayList<>(files)) {
            Chip chip = new Chip(requireContext());
            chip.setText(FileParts.displayName(requireContext(), uri));
            chip.setCloseIconVisible(true);
            chip.setOnCloseIconClickListener(v -> {
                files.remove(uri);
                renderFiles();
            });
            chipFiles.addView(chip);
        }
        chipFiles.setVisibility(files.isEmpty() ? View.GONE : View.VISIBLE);
    }

    private void submitAnalysis() {
        String text = etAnalysisText.getText() != null ? etAnalysisText.getText().toString().trim() : "";
        String rawUrls = etAnalysisUrl.getText() != null ? etAnalysisUrl.getText().toString().trim() : "";
        JSONArray urls = new JSONArray();
        for (String url : rawUrls.split("[\\s,]+")) {
            if (url.isEmpty()) continue;
            if (!url.startsWith("http://") && !url.startsWith("https://")) {
                etAnalysisUrl.setError(getString(R.string.analyze_bad_url, url));
                return;
            }
            urls.put(url);
        }
        if (text.isEmpty() && urls.length() == 0 && files.isEmpty()) {
            Toast.makeText(getContext(), R.string.analyze_empty, Toast.LENGTH_SHORT).show();
            return;
        }
        List<MultipartBody.Part> parts = new ArrayList<>();
        try {
            for (Uri uri : files) parts.add(FileParts.part(requireContext(), "files", uri));
        } catch (Exception e) {
            Toast.makeText(getContext(), R.string.error_file, Toast.LENGTH_LONG).show();
            return;
        }

        btnSubmitAnalysis.setEnabled(false);
        btnSubmitAnalysis.setText(R.string.analyze_sending);
        ApiClient.getApiService().createAnalysis(FileParts.text(text), FileParts.text(urls.toString()), parts)
                .enqueue(new ApiCallback<AnalysisOut>(getViewLifecycleOwner()) {
                    @Override
                    public void onSuccess(AnalysisOut analysis) {
                        etAnalysisText.setText("");
                        etAnalysisUrl.setText("");
                        files.clear();
                        renderFiles();
                        // L'analyse tourne en tâche de fond : la page Résultat suit sa progression.
                        startActivity(ResultActivity.intent(requireContext(), analysis.id));
                    }

                    @Override
                    public void onFinally() {
                        btnSubmitAnalysis.setEnabled(true);
                        btnSubmitAnalysis.setText(R.string.analyze_submit);
                    }
                });
    }
}
