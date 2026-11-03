package com.hoeaona.mobile.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.model.PostPage;
import com.hoeaona.mobile.util.Session;

public class FeedFragment extends Fragment {
    private static final int PAGE = 20;

    private SwipeRefreshLayout swipeRefresh;
    private TextInputEditText etSearch;
    private TextView tvEmpty;
    private PostAdapter adapter;
    private int loaded, total;
    private boolean loading;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_feed, container, false);
        swipeRefresh = view.findViewById(R.id.swipeRefresh);
        RecyclerView recyclerView = view.findViewById(R.id.recyclerView);
        FloatingActionButton fabCreatePost = view.findViewById(R.id.fabCreatePost);
        etSearch = view.findViewById(R.id.etSearch);
        tvEmpty = view.findViewById(R.id.tvEmpty);

        LinearLayoutManager layout = new LinearLayoutManager(getContext());
        recyclerView.setLayoutManager(layout);
        adapter = new PostAdapter(new PostActions(requireContext(), getViewLifecycleOwner(), new PostActions.Listener() {
            @Override public void onPostChanged(Post post) { adapter.replace(post); }
            @Override public void onPostDeleted(Post post) { adapter.remove(post); }
        }));
        recyclerView.setAdapter(adapter);
        recyclerView.addOnScrollListener(new RecyclerView.OnScrollListener() {
            @Override
            public void onScrolled(@NonNull RecyclerView rv, int dx, int dy) {
                if (dy > 0 && !loading && loaded < total && layout.findLastVisibleItemPosition() >= loaded - 4) {
                    loadPosts(false);
                }
            }
        });

        swipeRefresh.setOnRefreshListener(() -> loadPosts(true));
        etSearch.setOnEditorActionListener((v, actionId, e) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                loadPosts(true);
                return true;
            }
            return false;
        });
        fabCreatePost.setOnClickListener(v -> startActivity(new Intent(requireContext(), CreatePostActivity.class)));
        // Lecteur : lire, aimer, commenter ; pas de publication.
        boolean reader = Session.isReader(requireContext());
        fabCreatePost.setVisibility(reader ? View.GONE : View.VISIBLE);
        TextView title = view.findViewById(R.id.tvFeedTitle);
        title.setText(reader ? R.string.feed_title_reader : R.string.feed_title);
        view.findViewById(R.id.tvReaderIntro).setVisibility(reader ? View.VISIBLE : View.GONE);
        return view;
    }

    @Override
    public void onResume() {
        super.onResume();
        loadPosts(true);
    }

    private void loadPosts(boolean reset) {
        loading = true;
        swipeRefresh.setRefreshing(true);
        String q = etSearch.getText() != null ? etSearch.getText().toString().trim() : "";
        int offset = reset ? 0 : loaded;
        ApiClient.getApiService().listPosts(q, null, PAGE, offset).enqueue(new ApiCallback<PostPage>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(PostPage body) {
                total = body.total;
                if (reset) adapter.setPosts(body.items);
                else adapter.addPosts(body.items);
                loaded = offset + body.items.size();
                tvEmpty.setVisibility(loaded == 0 ? View.VISIBLE : View.GONE);
            }

            @Override
            public void onFinally() {
                loading = false;
                swipeRefresh.setRefreshing(false);
            }
        });
    }
}
