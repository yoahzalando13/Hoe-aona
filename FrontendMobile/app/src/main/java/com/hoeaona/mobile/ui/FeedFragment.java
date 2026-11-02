package com.hoeaona.mobile.ui;

import android.app.AlertDialog;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.model.PostPage;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.ArrayList;

public class FeedFragment extends Fragment {
    private SwipeRefreshLayout swipeRefresh;
    private RecyclerView recyclerView;
    private FloatingActionButton fabCreatePost;
    private PostAdapter adapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_feed, container, false);
        swipeRefresh = view.findViewById(R.id.swipeRefresh);
        recyclerView = view.findViewById(R.id.recyclerView);
        fabCreatePost = view.findViewById(R.id.fabCreatePost);

        recyclerView.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new PostAdapter(new ArrayList<>(), post -> {
            if (post.isLiked()) {
                ApiClient.getApiService().unlikePost(post.getId()).enqueue(new Callback<Post>() {
                    @Override
                    public void onResponse(Call<Post> call, Response<Post> response) {
                        loadPosts();
                    }
                    @Override
                    public void onFailure(Call<Post> call, Throwable t) {}
                });
            } else {
                ApiClient.getApiService().likePost(post.getId()).enqueue(new Callback<Post>() {
                    @Override
                    public void onResponse(Call<Post> call, Response<Post> response) {
                        loadPosts();
                    }
                    @Override
                    public void onFailure(Call<Post> call, Throwable t) {}
                });
            }
        });
        recyclerView.setAdapter(adapter);

        swipeRefresh.setOnRefreshListener(this::loadPosts);

        fabCreatePost.setOnClickListener(v -> showCreatePostDialog());

        loadPosts();
        return view;
    }

    private void loadPosts() {
        swipeRefresh.setRefreshing(true);
        ApiClient.getApiService().listPosts(null, null, 20, 0).enqueue(new Callback<PostPage>() {
            @Override
            public void onResponse(Call<PostPage> call, Response<PostPage> response) {
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setPosts(response.body().getItems());
                }
            }

            @Override
            public void onFailure(Call<PostPage> call, Throwable t) {
                swipeRefresh.setRefreshing(false);
                Toast.makeText(getContext(), "Erreur de chargement du feed", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void showCreatePostDialog() {
        EditText input = new EditText(getContext());
        input.setHint("Partagez une information ou une analyse...");
        new AlertDialog.Builder(getContext())
                .setTitle("Créer une publication")
                .setView(input)
                .setPositiveButton("Publier", (dialog, which) -> {
                    String text = input.getText().toString().trim();
                    if (!text.isEmpty()) {
                        okhttp3.RequestBody body = okhttp3.RequestBody.create(okhttp3.MediaType.parse("text/plain"), text);
                        ApiClient.getApiService().createPost(body, null, null).enqueue(new Callback<Post>() {
                            @Override
                            public void onResponse(Call<Post> call, Response<Post> response) {
                                if (response.isSuccessful()) {
                                    Toast.makeText(getContext(), "Publication créée", Toast.LENGTH_SHORT).show();
                                    loadPosts();
                                }
                            }
                            @Override
                            public void onFailure(Call<Post> call, Throwable t) {}
                        });
                    }
                })
                .setNegativeButton("Annuler", null)
                .show();
    }
}
