package com.hoeaona.mobile.ui;

import android.content.Context;
import android.content.Intent;
import android.view.View;
import android.widget.EditText;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.widget.PopupMenu;
import androidx.lifecycle.LifecycleOwner;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.Post;

import java.util.Collections;

/** Actions sur une publication, communes au fil, au profil, au détail et à la modération. */
public class PostActions {
    public interface Listener {
        void onPostChanged(Post post);
        void onPostDeleted(Post post);
    }

    private final Context context;
    private final LifecycleOwner owner;
    private final Listener listener;

    public PostActions(Context context, LifecycleOwner owner, Listener listener) {
        this.context = context;
        this.owner = owner;
        this.listener = listener;
    }

    public void openAnalysis(String analysisId) {
        context.startActivity(ResultActivity.intent(context, analysisId));
    }

    public void openPost(Post post) {
        context.startActivity(new Intent(context, PostActivity.class).putExtra(PostActivity.EXTRA_ID, post.id));
    }

    public void openProfile(String userId) {
        context.startActivity(new Intent(context, ProfileActivity.class).putExtra(ProfileActivity.EXTRA_ID, userId));
    }

    public void toggleLike(Post post) {
        (post.liked ? ApiClient.getApiService().unlikePost(post.id) : ApiClient.getApiService().likePost(post.id))
                .enqueue(changed());
    }

    public void showMenu(View anchor, Post post) {
        PopupMenu menu = new PopupMenu(context, anchor);
        if (post.can_edit) menu.getMenu().add(0, 1, 0, R.string.edit);
        if (post.can_moderate) menu.getMenu().add(0, 2, 1, post.hidden ? R.string.post_unhide : R.string.post_hide);
        if (post.can_edit || post.can_moderate) menu.getMenu().add(0, 3, 2, R.string.delete);
        menu.setOnMenuItemClickListener(item -> {
            switch (item.getItemId()) {
                case 1: edit(post); return true;
                case 2:
                    (post.hidden ? ApiClient.getApiService().unhidePost(post.id)
                            : ApiClient.getApiService().hidePost(post.id)).enqueue(changed());
                    return true;
                case 3: delete(post); return true;
                default: return false;
            }
        });
        menu.show();
    }

    private void edit(Post post) {
        EditText input = new EditText(context);
        input.setText(post.body);
        input.setMinLines(3);
        int pad = (int) (16 * context.getResources().getDisplayMetrics().density);
        input.setPadding(pad, pad, pad, pad);
        new AlertDialog.Builder(context).setTitle(R.string.post_edit_title).setView(input)
                .setPositiveButton(R.string.save, (d, w) -> {
                    String body = input.getText().toString().trim();
                    if (!body.isEmpty()) {
                        ApiClient.getApiService().editPost(post.id, Collections.singletonMap("body", body))
                                .enqueue(changed());
                    }
                })
                .setNegativeButton(R.string.cancel, null).show();
    }

    private void delete(Post post) {
        new AlertDialog.Builder(context).setMessage(R.string.post_delete_confirm)
                .setPositiveButton(R.string.delete, (d, w) -> ApiClient.getApiService().deletePost(post.id)
                        .enqueue(new ApiCallback<Void>(owner) {
                            @Override
                            public void onSuccess(Void body) {
                                listener.onPostDeleted(post);
                            }
                        }))
                .setNegativeButton(R.string.cancel, null).show();
    }

    private ApiCallback<Post> changed() {
        return new ApiCallback<Post>(owner) {
            @Override
            public void onSuccess(Post body) {
                listener.onPostChanged(body);
            }
        };
    }
}
