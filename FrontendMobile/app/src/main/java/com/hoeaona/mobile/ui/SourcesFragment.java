package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
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
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.OfficialSource;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.ArrayList;
import java.util.List;

public class SourcesFragment extends Fragment {
    private TextInputEditText etSearchSources;
    private SwipeRefreshLayout swipeRefreshSources;
    private RecyclerView recyclerSources;
    private SourceAdapter adapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_sources, container, false);
        etSearchSources = view.findViewById(R.id.etSearchSources);
        swipeRefreshSources = view.findViewById(R.id.swipeRefreshSources);
        recyclerSources = view.findViewById(R.id.recyclerSources);

        recyclerSources.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new SourceAdapter(new ArrayList<>());
        recyclerSources.setAdapter(adapter);

        swipeRefreshSources.setOnRefreshListener(() -> loadSources(""));

        etSearchSources.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                loadSources(s.toString());
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        loadSources("");
        return view;
    }

    private void loadSources(String q) {
        swipeRefreshSources.setRefreshing(true);
        ApiClient.getApiService().listSources(q, true).enqueue(new Callback<List<OfficialSource>>() {
            @Override
            public void onResponse(Call<List<OfficialSource>> call, Response<List<OfficialSource>> response) {
                swipeRefreshSources.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setSources(response.body());
                }
            }

            @Override
            public void onFailure(Call<List<OfficialSource>> call, Throwable t) {
                swipeRefreshSources.setRefreshing(false);
            }
        });
    }
}
