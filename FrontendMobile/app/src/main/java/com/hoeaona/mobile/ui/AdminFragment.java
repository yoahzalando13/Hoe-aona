package com.hoeaona.mobile.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.tabs.TabLayout;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.PlatformStats;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.model.PostPage;
import com.hoeaona.mobile.model.User;
import com.hoeaona.mobile.ui.widget.Ledger;

import java.util.List;

/** Administration : statistiques de la plateforme, comptes (rôle, activation), modération du fil. */
public class AdminFragment extends Fragment {
    private LinearLayout layoutLedger;
    private LinearLayout layoutUsers;
    private RecyclerView recyclerPosts;
    private PostAdapter postAdapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_admin, container, false);
        layoutLedger = view.findViewById(R.id.layoutLedger);
        layoutUsers = view.findViewById(R.id.layoutUsers);
        recyclerPosts = view.findViewById(R.id.recyclerPosts);
        TabLayout tabs = view.findViewById(R.id.tabs);
        View scrollUsers = view.findViewById(R.id.scrollUsers);

        recyclerPosts.setLayoutManager(new LinearLayoutManager(requireContext()));
        postAdapter = new PostAdapter(new PostActions(requireContext(), getViewLifecycleOwner(), new PostActions.Listener() {
            @Override public void onPostChanged(Post post) { postAdapter.replace(post); }
            @Override public void onPostDeleted(Post post) { postAdapter.remove(post); }
        }));
        recyclerPosts.setAdapter(postAdapter);

        tabs.addTab(tabs.newTab().setText(R.string.admin_users));
        tabs.addTab(tabs.newTab().setText(R.string.admin_posts));
        tabs.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override
            public void onTabSelected(TabLayout.Tab tab) {
                boolean users = tab.getPosition() == 0;
                scrollUsers.setVisibility(users ? View.VISIBLE : View.GONE);
                recyclerPosts.setVisibility(users ? View.GONE : View.VISIBLE);
            }
            @Override public void onTabUnselected(TabLayout.Tab tab) {}
            @Override public void onTabReselected(TabLayout.Tab tab) {}
        });

        loadStats();
        loadUsers();
        loadPosts();
        return view;
    }

    private void loadStats() {
        ApiClient.getApiService().adminStats().enqueue(new ApiCallback<PlatformStats>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(PlatformStats s) {
                Ledger.render(layoutLedger, new String[][]{
                        {String.valueOf(s.active_users), getString(R.string.admin_fig_active, s.users)},
                        {String.valueOf(s.admins), getString(R.string.admin_fig_admins)},
                        {String.valueOf(s.analyses), getString(R.string.admin_fig_analyses)},
                        {String.valueOf(s.posts), getString(R.string.admin_fig_posts, s.hidden_posts)},
                        {String.valueOf(s.comments), getString(R.string.admin_fig_comments)},
                        {String.valueOf(s.likes), getString(R.string.admin_fig_likes)},
                }, 3);
            }
        });
    }

    private void loadUsers() {
        ApiClient.getApiService().adminUsers("").enqueue(new ApiCallback<List<User>>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(List<User> users) {
                layoutUsers.removeAllViews();
                for (User u : users) layoutUsers.addView(userRow(u));
            }
        });
    }

    private View userRow(User u) {
        View row = LayoutInflater.from(requireContext()).inflate(R.layout.item_admin_user, layoutUsers, false);
        ((TextView) row.findViewById(R.id.tvName)).setText(u.display_name + (u.active ? "" : " — " + getString(R.string.admin_inactive)));
        ((TextView) row.findViewById(R.id.tvMeta)).setText(getString(R.string.admin_user_meta, u.email,
                u.isAdmin() ? getString(R.string.role_admin) : getString(R.string.role_media), u.analyses_count, u.posts_count));
        MaterialButton role = row.findViewById(R.id.btnRole);
        role.setText(u.isAdmin() ? R.string.admin_make_media : R.string.admin_make_admin);
        role.setOnClickListener(v -> update(u, "role", u.isAdmin() ? "media" : "admin"));
        MaterialButton active = row.findViewById(R.id.btnActive);
        active.setText(u.active ? R.string.admin_deactivate : R.string.admin_activate);
        active.setOnClickListener(v -> update(u, "active", null));
        return row;
    }

    private void update(User u, String field, String role) {
        JsonObject patch = new JsonObject();
        if ("role".equals(field)) patch.addProperty("role", role);
        else patch.addProperty("active", !u.active);
        ApiClient.getApiService().adminUpdateUser(u.id, patch).enqueue(new ApiCallback<User>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(User body) {
                loadUsers();
                loadStats();
            }
        });
    }

    private void loadPosts() {
        ApiClient.getApiService().adminPosts("", 50, 0).enqueue(new ApiCallback<PostPage>(getViewLifecycleOwner()) {
            @Override
            public void onSuccess(PostPage body) {
                postAdapter.setPosts(body.items);
            }
        });
    }
}
