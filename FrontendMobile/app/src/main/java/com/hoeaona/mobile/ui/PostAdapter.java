package com.hoeaona.mobile.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.button.MaterialButton;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.Post;
import java.util.List;

public class PostAdapter extends RecyclerView.Adapter<PostAdapter.PostViewHolder> {
    private List<Post> posts;
    private final OnPostListener listener;

    public interface OnPostListener {
        void onLikeClick(Post post);
    }

    public PostAdapter(List<Post> posts, OnPostListener listener) {
        this.posts = posts;
        this.listener = listener;
    }

    public void setPosts(List<Post> posts) {
        this.posts = posts;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public PostViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_post, parent, false);
        return new PostViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull PostViewHolder holder, int position) {
        Post post = posts.get(position);
        holder.tvAuthorName.setText(post.getAuthorName() != null ? post.getAuthorName() : "Anonyme");
        holder.tvBody.setText(post.getBody());
        holder.btnLike.setText("J'aime (" + post.getLikes() + ")");
        holder.btnLike.setOnClickListener(v -> {
            if (listener != null) listener.onLikeClick(post);
        });
    }

    @Override
    public int getItemCount() {
        return posts != null ? posts.size() : 0;
    }

    static class PostViewHolder extends RecyclerView.ViewHolder {
        TextView tvAuthorName, tvBody;
        MaterialButton btnLike;

        public PostViewHolder(@NonNull View itemView) {
            super(itemView);
            tvAuthorName = itemView.findViewById(R.id.tvAuthorName);
            tvBody = itemView.findViewById(R.id.tvBody);
            btnLike = itemView.findViewById(R.id.btnLike);
        }
    }
}
