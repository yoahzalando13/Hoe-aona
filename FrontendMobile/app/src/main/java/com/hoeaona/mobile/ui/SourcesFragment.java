package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.OfficialContact;

import java.util.List;

/** Annuaire des sources officielles : recherche, appel, e-mail, site. */
public class SourcesFragment extends Fragment {
    private TextInputEditText etSearchSources;
    private SwipeRefreshLayout swipeRefreshSources;
    private SourceAdapter adapter;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable search = this::loadSources;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_sources, container, false);
        etSearchSources = view.findViewById(R.id.etSearchSources);
        swipeRefreshSources = view.findViewById(R.id.swipeRefreshSources);
        RecyclerView recyclerSources = view.findViewById(R.id.recyclerSources);

        recyclerSources.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new SourceAdapter();
        recyclerSources.setAdapter(adapter);

        swipeRefreshSources.setOnRefreshListener(this::loadSources);
        etSearchSources.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override
            public void afterTextChanged(Editable s) {
                // Une requête après la frappe, pas une par caractère.
                handler.removeCallbacks(search);
                handler.postDelayed(search, 350);
            }
        });

        loadSources();
        return view;
    }

    @Override
    public void onDestroyView() {
        handler.removeCallbacks(search);
        super.onDestroyView();
    }

    private void loadSources() {
        if (getView() == null) return;
        swipeRefreshSources.setRefreshing(true);
        String q = etSearchSources.getText() != null ? etSearchSources.getText().toString().trim() : "";
        ApiClient.getApiService().listSources(q, false).enqueue(new ApiCallback<List<OfficialContact>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<OfficialContact> body) {
                adapter.setSources(body);
            }

            @Override
            public void onFinally() {
                swipeRefreshSources.setRefreshing(false);
            }
        });
    }
}
