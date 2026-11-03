package com.hoeaona.mobile.ui;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.content.FileProvider;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.chip.ChipGroup;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisPage;
import com.hoeaona.mobile.model.AnalysisStats;
import com.hoeaona.mobile.ui.widget.Ledger;
import com.hoeaona.mobile.util.Format;
import okhttp3.ResponseBody;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Locale;

/** Mon espace : base personnelle des analyses (statistiques, recherche, filtres, suivi éditorial, export). */
public class WorkspaceFragment extends Fragment {
    private static final int PAGE = 30;

    private SwipeRefreshLayout swipe;
    private TextInputEditText etSearch;
    private ChipGroup chipsWorkflow;
    private TextView tvLegend, tvEmpty;
    private LinearLayout layoutLedger, stackVerdicts;
    private AnalysisAdapter adapter;
    private int loaded, total;
    private boolean loading;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_workspace, container, false);
        swipe = view.findViewById(R.id.swipeRefresh);
        etSearch = view.findViewById(R.id.etSearch);
        chipsWorkflow = view.findViewById(R.id.chipsWorkflow);
        tvLegend = view.findViewById(R.id.tvLegend);
        layoutLedger = view.findViewById(R.id.layoutLedger);
        stackVerdicts = view.findViewById(R.id.stackVerdicts);
        tvEmpty = view.findViewById(R.id.tvEmpty);
        RecyclerView recycler = view.findViewById(R.id.recyclerView);

        LinearLayoutManager layout = new LinearLayoutManager(requireContext());
        recycler.setLayoutManager(layout);
        adapter = new AnalysisAdapter(a -> startActivity(ResultActivity.intent(requireContext(), a.id)));
        recycler.setAdapter(adapter);
        recycler.addOnScrollListener(new RecyclerView.OnScrollListener() {
            @Override
            public void onScrolled(@NonNull RecyclerView rv, int dx, int dy) {
                if (dy > 0 && !loading && loaded < total && layout.findLastVisibleItemPosition() >= loaded - 4) {
                    load(false);
                }
            }
        });

        swipe.setOnRefreshListener(() -> load(true));
        chipsWorkflow.setOnCheckedStateChangeListener((group, ids) -> load(true));
        etSearch.setOnEditorActionListener((v, actionId, e) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                load(true);
                return true;
            }
            return false;
        });
        view.findViewById(R.id.btnExport).setOnClickListener(v -> exportCsv());
        return view;
    }

    @Override
    public void onResume() {
        super.onResume();
        load(true);
        loadStats();
    }

    private String selectedWorkflow() {
        int id = chipsWorkflow.getCheckedChipId();
        if (id == R.id.chipATraiter) return "a_traiter";
        if (id == R.id.chipEnRevue) return "en_revue";
        if (id == R.id.chipValide) return "valide";
        if (id == R.id.chipPublie) return "publie";
        if (id == R.id.chipArchive) return "archive";
        return null;
    }

    private void loadStats() {
        ApiClient.getApiService().analysisStats().enqueue(new ApiCallback<AnalysisStats>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(AnalysisStats s) {
                Ledger.render(layoutLedger, new String[][]{
                        {String.valueOf(s.total), getString(s.total == 1 ? R.string.workspace_saved_one : R.string.workspace_saved_other)},
                        {s.average_score == null ? "–" : String.format(Locale.getDefault(), "%.1f", s.average_score),
                                getString(R.string.workspace_average_label)},
                        {String.valueOf(count(s, "a_traiter") + count(s, "en_revue")), getString(R.string.workspace_pending_label)},
                        {String.valueOf(count(s, "publie")), getString(R.string.workspace_published_label)},
                }, 2);
                renderVerdicts(s);
            }
        });
    }

    private static int count(AnalysisStats s, String workflow) {
        Integer n = s.by_workflow == null ? null : s.by_workflow.get(workflow);
        return n == null ? 0 : n;
    }

    /** Barre empilée des verdicts (largeurs proportionnelles), légende en dessous. */
    private void renderVerdicts(AnalysisStats s) {
        stackVerdicts.removeAllViews();
        int total = 0;
        if (s.by_verdict != null) for (Integer n : s.by_verdict.values()) total += n == null ? 0 : n;
        stackVerdicts.setVisibility(total > 0 ? View.VISIBLE : View.GONE);
        if (total == 0) {
            tvLegend.setText("");
            return;
        }
        StringBuilder legend = new StringBuilder();
        int gap = (int) getResources().getDisplayMetrics().density;
        for (String key : new String[]{"fiable", "plutot_fiable", "a_verifier", "douteux"}) {
            Integer n = s.by_verdict.get(key);
            if (n == null || n == 0) continue;
            View part = new View(requireContext());
            part.setBackgroundColor(requireContext().getColor(Format.verdictColor(key)));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, n);
            lp.setMarginEnd(gap);
            stackVerdicts.addView(part, lp);
            legend.append("■ ").append(Format.verdict(requireContext(), key)).append(" ").append(n).append("    ");
        }
        tvLegend.setText(legend.toString().trim());
    }

    private void load(boolean reset) {
        loading = true;
        swipe.setRefreshing(true);
        String q = etSearch.getText() != null ? etSearch.getText().toString().trim() : "";
        int offset = reset ? 0 : loaded;
        ApiClient.getApiService().listAnalyses(q, null, selectedWorkflow(), null, PAGE, offset)
                .enqueue(new ApiCallback<AnalysisPage>(getViewLifecycleOwner()) {
                    @Override
                    public void onSuccess(AnalysisPage body) {
                        total = body.total;
                        if (reset) adapter.setAnalyses(body.items);
                        else adapter.addAnalyses(body.items);
                        loaded = offset + body.items.size();
                        tvEmpty.setVisibility(loaded == 0 ? View.VISIBLE : View.GONE);
                    }

                    @Override
                    public void onFinally() {
                        loading = false;
                        swipe.setRefreshing(false);
                    }
                });
    }

    /** Export CSV de l'espace : téléchargé avec la session puis partagé (tableur, e-mail, Drive…). */
    private void exportCsv() {
        ApiClient.getApiService().exportCsv().enqueue(new ApiCallback<ResponseBody>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(ResponseBody body) {
                File file = new File(requireContext().getCacheDir(), "hoe-aona-analyses.csv");
                try (InputStream in = body.byteStream(); OutputStream out = new FileOutputStream(file)) {
                    byte[] buffer = new byte[8192];
                    int n;
                    while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
                } catch (Exception e) {
                    Toast.makeText(requireContext(), R.string.error_file, Toast.LENGTH_LONG).show();
                    return;
                }
                Uri uri = FileProvider.getUriForFile(requireContext(), requireContext().getPackageName() + ".files", file);
                Intent share = new Intent(Intent.ACTION_SEND).setType("text/csv").putExtra(Intent.EXTRA_STREAM, uri)
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivity(Intent.createChooser(share, getString(R.string.workspace_export)));
            }
        });
    }
}
