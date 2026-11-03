package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.textfield.TextInputEditText;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Comment;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.util.Format;

import java.util.Collections;
import java.util.List;

/** Publication et ses commentaires. */
public class PostActivity extends AppCompatActivity {
    public static final String EXTRA_ID = "post_id";

    private String postId;
    private PostAdapter.PostViewHolder postHolder;
    private PostActions actions;
    private LinearLayout layoutComments;
    private TextInputEditText etComment;
    private MaterialButton btnSend;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_post);
        postId = getIntent().getStringExtra(EXTRA_ID);
        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        ViewGroup postContainer = findViewById(R.id.postContainer);
        View postView = LayoutInflater.from(this).inflate(R.layout.item_post, postContainer, false);
        postContainer.addView(postView);
        postHolder = new PostAdapter.PostViewHolder(postView);
        actions = new PostActions(this, this, new PostActions.Listener() {
            @Override public void onPostChanged(Post post) { bindPost(post); }
            @Override public void onPostDeleted(Post post) { finish(); }
        });

        layoutComments = findViewById(R.id.layoutComments);
        etComment = findViewById(R.id.etComment);
        btnSend = findViewById(R.id.btnSend);
        btnSend.setOnClickListener(v -> sendComment());

        ApiClient.getApiService().getPost(postId).enqueue(new ApiCallback<Post>(this) {
            @Override
            public void onSuccess(Post body) {
                bindPost(body);
            }

            @Override
            public void onError(int code, String message) {
                super.onError(code, message);
                finish();
            }
        });
        loadComments();
    }

    private void bindPost(Post post) {
        PostAdapter.bind(postHolder, post, actions);
        postHolder.btnComments.setOnClickListener(v -> etComment.requestFocus());
    }

    private void loadComments() {
        ApiClient.getApiService().getComments(postId).enqueue(commentsCallback());
    }

    private ApiCallback<List<Comment>> commentsCallback() {
        return new ApiCallback<List<Comment>>(this) {
            @Override
            public void onSuccess(List<Comment> body) {
                showComments(body);
            }

            @Override
            public void onFinally() {
                btnSend.setEnabled(true);
            }
        };
    }

    private void showComments(List<Comment> comments) {
        layoutComments.removeAllViews();
        findViewById(R.id.tvNoComments).setVisibility(comments.isEmpty() ? View.VISIBLE : View.GONE);
        for (Comment comment : comments) {
            View row = LayoutInflater.from(this).inflate(R.layout.item_comment, layoutComments, false);
            ((TextView) row.findViewById(R.id.tvAuthor)).setText(comment.author_name);
            ((TextView) row.findViewById(R.id.tvDate)).setText(Format.date(comment.created_at));
            ((TextView) row.findViewById(R.id.tvBody)).setText(comment.body);
            View delete = row.findViewById(R.id.btnDelete);
            delete.setVisibility(comment.can_delete ? View.VISIBLE : View.GONE);
            delete.setOnClickListener(v -> new AlertDialog.Builder(this).setMessage(R.string.comment_delete_confirm)
                    .setPositiveButton(R.string.delete, (d, w) -> ApiClient.getApiService()
                            .deleteComment(postId, comment.id).enqueue(new ApiCallback<Void>(this) {
                                @Override
                                public void onSuccess(Void body) {
                                    loadComments();
                                }
                            }))
                    .setNegativeButton(R.string.cancel, null).show());
            row.findViewById(R.id.tvAuthor).setOnClickListener(v -> actions.openProfile(comment.author_id));
            layoutComments.addView(row);
        }
    }

    private void sendComment() {
        String body = etComment.getText() != null ? etComment.getText().toString().trim() : "";
        if (body.isEmpty()) return;
        btnSend.setEnabled(false);
        ApiClient.getApiService().addComment(postId, Collections.singletonMap("body", body))
                .enqueue(new ApiCallback<List<Comment>>(this) {
                    @Override
                    public void onSuccess(List<Comment> comments) {
                        etComment.setText("");
                        showComments(comments);
                    }

                    @Override
                    public void onFinally() {
                        btnSend.setEnabled(true);
                    }
                });
    }
}
