package com.hoeaona.mobile.ui;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.util.Format;
import com.hoeaona.mobile.util.ImageLoader;

import java.util.ArrayList;
import java.util.List;

public class PostAdapter extends RecyclerView.Adapter<PostAdapter.PostViewHolder> {
    private List<Post> posts = new ArrayList<>();
    private final PostActions actions;

    public PostAdapter(PostActions actions) {
        this.actions = actions;
    }

    public void setPosts(List<Post> posts) {
        this.posts = posts != null ? posts : new ArrayList<>();
        notifyDataSetChanged();
    }

    public void addPosts(List<Post> more) {
        int start = posts.size();
        posts.addAll(more);
        notifyItemRangeInserted(start, more.size());
    }

    public void replace(Post post) {
        for (int i = 0; i < posts.size(); i++) {
            if (posts.get(i).id.equals(post.id)) {
                posts.set(i, post);
                notifyItemChanged(i);
                return;
            }
        }
    }

    public void remove(Post post) {
        int i = posts.indexOf(post);
        if (i >= 0) {
            posts.remove(i);
            notifyItemRemoved(i);
        }
    }

    @NonNull
    @Override
    public PostViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_post, parent, false);
        return new PostViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull PostViewHolder holder, int position) {
        bind(holder, posts.get(position), actions);
    }

    /** Partagé avec l'écran de détail d'une publication. */
    static void bind(PostViewHolder holder, Post post, PostActions actions) {
        Context c = holder.itemView.getContext();
        String org = post.author_organization != null && !post.author_organization.isEmpty()
                ? " · " + post.author_organization : "";
        holder.tvAuthorName.setText(post.author_name + org);
        holder.tvDate.setText(Format.date(post.created_at));
        holder.tvBody.setText(post.body);
        holder.tvBody.setVisibility(post.body == null || post.body.isEmpty() ? View.GONE : View.VISIBLE);
        holder.tvHidden.setVisibility(post.hidden ? View.VISIBLE : View.GONE);
        ImageLoader.load(holder.ivImage, post.image_url);

        if (post.analysis != null) {
            holder.cardAnalysis.setVisibility(View.VISIBLE);
            holder.tvAnalysisTitle.setText(post.analysis.title);
            holder.tvAnalysisVerdict.setText(c.getString(R.string.score_verdict, Format.score(post.analysis.global_score),
                    Format.verdict(c, post.analysis.verdict)));
            holder.tvAnalysisVerdict.setTextColor(c.getColor(Format.verdictColor(post.analysis.verdict)));
            holder.cardAnalysis.setOnClickListener(v -> actions.openAnalysis(post.analysis.id));
        } else {
            holder.cardAnalysis.setVisibility(View.GONE);
        }

        holder.btnLike.setText(c.getString(R.string.post_likes, post.likes));
        holder.btnLike.setIconResource(post.liked ? R.drawable.ic_heart : R.drawable.ic_heart_outline);
        holder.btnLike.setOnClickListener(v -> actions.toggleLike(post));
        holder.btnComments.setText(c.getString(R.string.post_comments, post.comments_count));
        holder.btnComments.setOnClickListener(v -> actions.openPost(post));
        holder.tvAuthorName.setOnClickListener(v -> actions.openProfile(post.author_id));
        holder.btnMenu.setVisibility(post.can_edit || post.can_moderate ? View.VISIBLE : View.GONE);
        holder.btnMenu.setOnClickListener(v -> actions.showMenu(v, post));
    }

    @Override
    public int getItemCount() {
        return posts.size();
    }

    static class PostViewHolder extends RecyclerView.ViewHolder {
        TextView tvAuthorName, tvDate, tvBody, tvHidden, tvAnalysisTitle, tvAnalysisVerdict;
        ImageView ivImage;
        MaterialCardView cardAnalysis;
        MaterialButton btnLike, btnComments;
        ImageButton btnMenu;

        public PostViewHolder(@NonNull View itemView) {
            super(itemView);
            tvAuthorName = itemView.findViewById(R.id.tvAuthorName);
            tvDate = itemView.findViewById(R.id.tvDate);
            tvBody = itemView.findViewById(R.id.tvBody);
            tvHidden = itemView.findViewById(R.id.tvHidden);
            ivImage = itemView.findViewById(R.id.ivImage);
            cardAnalysis = itemView.findViewById(R.id.cardAnalysis);
            tvAnalysisTitle = itemView.findViewById(R.id.tvAnalysisTitle);
            tvAnalysisVerdict = itemView.findViewById(R.id.tvAnalysisVerdict);
            btnLike = itemView.findViewById(R.id.btnLike);
            btnComments = itemView.findViewById(R.id.btnComments);
            btnMenu = itemView.findViewById(R.id.btnMenu);
        }
    }
}
