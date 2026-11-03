package com.hoeaona.mobile.ui;

import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AppNotification;
import com.hoeaona.mobile.util.Format;
import com.hoeaona.mobile.verify.VerificationActivity;
import com.hoeaona.mobile.verify.VerificationNotifier;

import java.util.List;

/** Historique des notifications de vérification physique. */
public class NotificationsFragment extends Fragment {
    private LinearLayout layoutList;
    private TextView tvEmpty;
    private SwipeRefreshLayout swipe;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_notifications, container, false);
        layoutList = view.findViewById(R.id.layoutList);
        tvEmpty = view.findViewById(R.id.tvEmpty);
        swipe = view.findViewById(R.id.swipeRefresh);
        swipe.setOnRefreshListener(this::load);
        return view;
    }

    @Override
    public void onResume() {
        super.onResume();
        load();
    }

    private void load() {
        swipe.setRefreshing(true);
        ApiClient.getApiService().notifications(false).enqueue(new ApiCallback<List<AppNotification>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<AppNotification> items) {
                layoutList.removeAllViews();
                tvEmpty.setVisibility(items.isEmpty() ? View.VISIBLE : View.GONE);
                boolean unread = false;
                for (AppNotification n : items) {
                    layoutList.addView(row(n));
                    unread |= !n.read;
                }
                if (unread) {
                    ApiClient.getApiService().markNotificationsRead(new JsonObject()).enqueue(new ApiCallback<Void>(null) {
                        @Override public void onSuccess(Void body) {}
                        @Override public void onError(int code, String message) {}
                    });
                }
            }

            @Override
            public void onFinally() {
                swipe.setRefreshing(false);
            }
        });
    }

    private View row(AppNotification n) {
        View row = LayoutInflater.from(requireContext()).inflate(R.layout.item_notification, layoutList, false);
        TextView title = row.findViewById(R.id.tvTitle);
        title.setText(VerificationNotifier.title(requireContext(), n));
        title.setTypeface(null, n.read ? Typeface.NORMAL : Typeface.BOLD);
        ((TextView) row.findViewById(R.id.tvBody)).setText(VerificationNotifier.body(requireContext(), n));
        ((TextView) row.findViewById(R.id.tvDate)).setText(Format.date(n.created_at));
        if (n.request != null) {
            row.setOnClickListener(v -> startActivity(new Intent(requireContext(), VerificationActivity.class)
                    .putExtra(VerificationActivity.EXTRA_ID, n.request.id)));
        }
        return row;
    }
}
