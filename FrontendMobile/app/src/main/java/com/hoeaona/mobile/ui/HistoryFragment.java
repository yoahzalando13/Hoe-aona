package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisPage;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.ArrayList;

public class HistoryFragment extends Fragment {
    private SwipeRefreshLayout swipeRefreshHistory;
    private RecyclerView recyclerHistory;
    private AnalysisAdapter adapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_history, container, false);
        swipeRefreshHistory = view.findViewById(R.id.swipeRefreshHistory);
        recyclerHistory = view.findViewById(R.id.recyclerHistory);

        recyclerHistory.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new AnalysisAdapter(new ArrayList<>(), analysis -> {
            Toast.makeText(getContext(), "Analyse : " + analysis.getTitle(), Toast.LENGTH_SHORT).show();
        });
        recyclerHistory.setAdapter(adapter);

        swipeRefreshHistory.setOnRefreshListener(this::loadHistory);
        loadHistory();
        return view;
    }

    private void loadHistory() {
        swipeRefreshHistory.setRefreshing(true);
        ApiClient.getApiService().listAnalyses(null, null, null, null, 50, 0).enqueue(new Callback<AnalysisPage>() {
            @Override
            public void onResponse(Call<AnalysisPage> call, Response<AnalysisPage> response) {
                swipeRefreshHistory.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setAnalyses(response.body().getItems());
                }
            }

            @Override
            public void onFailure(Call<AnalysisPage> call, Throwable t) {
                swipeRefreshHistory.setRefreshing(false);
                Toast.makeText(getContext(), "Erreur de chargement de l'historique", Toast.LENGTH_SHORT).show();
            }
        });
    }
}
