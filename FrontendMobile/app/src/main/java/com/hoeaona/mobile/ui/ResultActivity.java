package com.hoeaona.mobile.ui;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.progressindicator.LinearProgressIndicator;
import com.google.android.material.textfield.TextInputEditText;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.hoeaona.mobile.R;
import com.hoeaona.mobile.api.ApiCallback;
import com.hoeaona.mobile.api.ApiClient;
import com.hoeaona.mobile.model.AnalysisOut;
import com.hoeaona.mobile.model.AnalysisResult;
import com.hoeaona.mobile.model.AnalysisResult.Claim;
import com.hoeaona.mobile.model.OfficialContact;
import com.hoeaona.mobile.model.Post;
import com.hoeaona.mobile.util.ContactViews;
import com.hoeaona.mobile.util.Format;
import com.hoeaona.mobile.util.Links;
import com.hoeaona.mobile.ui.widget.ScoreScaleView;
import com.hoeaona.mobile.verify.CreateVerificationActivity;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Résultat d'une analyse : suivi en direct, scores, affirmations et preuves, article, suivi éditorial. */
public class ResultActivity extends AppCompatActivity {
    public static final String EXTRA_ID = "analysis_id";
    private static final String[] WORKFLOWS = {"a_traiter", "en_revue", "valide", "publie", "archive"};
    private static final long POLL_MS = 2000;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private String id;
    private AnalysisOut analysis;
    private boolean workspaceBound;

    private MaterialToolbar toolbar;
    private View layoutProgress, layoutContent, cardArticle, cardWorkspace;
    private LinearProgressIndicator progress;
    private TextView tvStep, tvEvents, tvError, tvScore, tvVerdict, tvSummary, tvOwner, tvWarnings;
    private TextView tvArticleTitle, tvArticleLead, tvArticleKeyPoints, tvArticleBody, tvArticleSources;
    private LinearLayout layoutCriteria, layoutClaims;
    private TextInputEditText etTitle, etTags, etNotes;
    private Spinner spWorkflow;

    private final Runnable poller = this::load;

    public static Intent intent(Context context, String analysisId) {
        return new Intent(context, ResultActivity.class).putExtra(EXTRA_ID, analysisId);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result);
        id = getIntent().getStringExtra(EXTRA_ID);
        toolbar = findViewById(R.id.toolbar);
        toolbar.setNavigationOnClickListener(v -> finish());

        layoutProgress = findViewById(R.id.layoutProgress);
        layoutContent = findViewById(R.id.layoutContent);
        cardArticle = findViewById(R.id.cardArticle);
        cardWorkspace = findViewById(R.id.cardWorkspace);
        progress = findViewById(R.id.progress);
        tvStep = findViewById(R.id.tvStep);
        tvEvents = findViewById(R.id.tvEvents);
        tvError = findViewById(R.id.tvError);
        tvScore = findViewById(R.id.tvScore);
        tvVerdict = findViewById(R.id.tvVerdict);
        tvSummary = findViewById(R.id.tvSummary);
        tvOwner = findViewById(R.id.tvOwner);
        tvWarnings = findViewById(R.id.tvWarnings);
        tvArticleTitle = findViewById(R.id.tvArticleTitle);
        tvArticleLead = findViewById(R.id.tvArticleLead);
        tvArticleKeyPoints = findViewById(R.id.tvArticleKeyPoints);
        tvArticleBody = findViewById(R.id.tvArticleBody);
        tvArticleSources = findViewById(R.id.tvArticleSources);
        layoutCriteria = findViewById(R.id.layoutCriteria);
        layoutClaims = findViewById(R.id.layoutClaims);
        etTitle = findViewById(R.id.etTitle);
        etTags = findViewById(R.id.etTags);
        etNotes = findViewById(R.id.etNotes);
        spWorkflow = findViewById(R.id.spWorkflow);

        String[] workflowLabels = new String[WORKFLOWS.length];
        for (int i = 0; i < WORKFLOWS.length; i++) workflowLabels[i] = Format.workflow(this, WORKFLOWS[i]);
        ArrayAdapter<String> workflowAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, workflowLabels);
        workflowAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spWorkflow.setAdapter(workflowAdapter);

        findViewById(R.id.btnSaveWorkspace).setOnClickListener(v -> saveWorkspace());
        findViewById(R.id.btnRegenerate).setOnClickListener(v -> regenerateArticle());
        findViewById(R.id.btnShareArticle).setOnClickListener(v -> shareArticle());
        findViewById(R.id.btnPublishArticle).setOnClickListener(v -> publish("article"));
        findViewById(R.id.btnPublishShort).setOnClickListener(v -> publish("court"));
        load();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(poller);
        super.onDestroy();
    }

    private void load() {
        ApiClient.getApiService().getAnalysis(id).enqueue(new ApiCallback<AnalysisOut>(this) {
            @Override
            public void onSuccess(AnalysisOut body) {
                bind(body);
                if (!body.isFinished()) handler.postDelayed(poller, POLL_MS);
            }

            @Override
            public void onError(int code, String message) {
                super.onError(code, message);
                if (code == 404) finish();
                else if (code == 0) handler.postDelayed(poller, POLL_MS * 3);  // réseau coupé : on réessaie
            }
        });
    }

    private void bind(AnalysisOut a) {
        analysis = a;
        toolbar.setTitle(a.title);
        buildMenu(a);
        boolean running = !a.isFinished();
        layoutProgress.setVisibility(running ? View.VISIBLE : View.GONE);
        if (running) {
            progress.setProgressCompat(a.progress, true);
            tvStep.setText(getString(R.string.result_step, a.progress, a.step));
            StringBuilder events = new StringBuilder();
            if (a.events != null) {
                for (int i = Math.max(0, a.events.size() - 6); i < a.events.size(); i++) {
                    events.append("• ").append(a.events.get(i).message).append('\n');
                }
            }
            tvEvents.setText(events.toString().trim());
        }
        tvError.setVisibility("error".equals(a.status) ? View.VISIBLE : View.GONE);
        tvError.setText(getString(R.string.result_error, a.error == null ? "" : a.error));

        tvOwner.setVisibility(a.editable ? View.GONE : View.VISIBLE);
        tvOwner.setText(getString(R.string.result_read_only, a.owner_name == null ? "?" : a.owner_name));
        cardWorkspace.setVisibility(a.editable ? View.VISIBLE : View.GONE);
        if (a.editable && !workspaceBound) {
            workspaceBound = true;  // ne pas écraser la saisie pendant le suivi en direct
            etTitle.setText(a.title);
            etTags.setText(a.tags == null ? "" : String.join(", ", a.tags));
            etNotes.setText(a.notes);
            for (int i = 0; i < WORKFLOWS.length; i++) if (WORKFLOWS[i].equals(a.workflow)) spWorkflow.setSelection(i);
        }

        AnalysisResult r = a.result;
        layoutContent.setVisibility(r != null ? View.VISIBLE : View.GONE);
        if (r == null) return;
        tvScore.setText(Format.scoreSpan(this, r.global_score));
        tvScore.setTextColor(getColor(Format.scoreColor(r.global_score)));
        ((ScoreScaleView) findViewById(R.id.scoreScale)).setScore(r.global_score);
        tvVerdict.setText(r.verdict_label);
        Format.stamp(tvVerdict, Format.scoreColor(r.global_score));
        tvSummary.setText(r.summary);
        tvWarnings.setVisibility(r.warnings == null || r.warnings.isEmpty() ? View.GONE : View.VISIBLE);
        if (r.warnings != null) tvWarnings.setText("⚠ " + String.join("\n⚠ ", r.warnings));

        layoutCriteria.removeAllViews();
        if (r.criteria != null) {
            for (AnalysisResult.Criterion criterion : r.criteria) {
                View row = LayoutInflater.from(this).inflate(R.layout.item_criterion, layoutCriteria, false);
                ((TextView) row.findViewById(R.id.tvLabel)).setText(criterion.label);
                TextView score = row.findViewById(R.id.tvScore);
                score.setText(Format.scoreSpan(this, criterion.score));
                score.setTextColor(getColor(Format.scoreColor(criterion.score)));
                ScoreScaleView scale = row.findViewById(R.id.scale);
                scale.setShowLabels(false);
                scale.setScore(criterion.score);
                ((TextView) row.findViewById(R.id.tvSummary)).setText(criterion.summary);
                layoutCriteria.addView(row);
            }
        }

        layoutClaims.removeAllViews();
        if (r.claims != null) {
            for (int i = 0; i < r.claims.size(); i++) layoutClaims.addView(claimView(r.claims.get(i), i + 1, a.editable));
        }
        bindArticle(r.article);
    }

    private void buildMenu(AnalysisOut a) {
        Menu menu = toolbar.getMenu();
        menu.clear();
        if (a.result != null && a.result.article != null) {
            menu.add(R.string.share).setOnMenuItemClickListener(i -> { shareArticle(); return true; });
        }
        if (a.editable) {
            menu.add(R.string.delete).setOnMenuItemClickListener(i -> { confirmDelete(); return true; });
        }
    }

    private View claimView(Claim claim, int n, boolean editable) {
        View view = LayoutInflater.from(this).inflate(R.layout.item_claim, layoutClaims, false);
        ((TextView) view.findViewById(R.id.tvClaimText)).setText(getString(R.string.result_claim_n, n, claim.text));
        TextView verdict = view.findViewById(R.id.tvClaimVerdict);
        verdict.setText(getString(R.string.score_verdict, Format.score(claim.truth_score), claim.verdict_label));
        Format.stamp(verdict, Format.verdictColor(claim.verdict));
        ((TextView) view.findViewById(R.id.tvConclusion)).setText(claim.conclusion);

        LinearLayout details = view.findViewById(R.id.layoutDetails);
        addList(details, R.string.result_arguments_for, claim.arguments_for);
        addList(details, R.string.result_arguments_against, claim.arguments_against);

        if (claim.evidence != null && !claim.evidence.isEmpty()) {
            addHeader(details, getString(R.string.result_evidence, claim.evidence.size()));
            for (AnalysisResult.Evidence e : claim.evidence) {
                View row = LayoutInflater.from(this).inflate(R.layout.item_evidence, details, false);
                ((TextView) row.findViewById(R.id.tvTitle)).setText(e.title);
                String meta = (e.official ? "✓ " + getString(R.string.result_official) + " · " : "") + e.publisher
                        + (e.published_at != null ? " · " + e.published_at.substring(0, Math.min(10, e.published_at.length())) : "")
                        + " · " + getString(R.string.result_reliability, Math.round(e.reliability * 100));
                ((TextView) row.findViewById(R.id.tvMeta)).setText(meta);
                TextView stance = row.findViewById(R.id.tvStance);
                stance.setText(stanceLabel(e.stance));
                stance.setTextColor(getColor("supports".equals(e.stance) ? R.color.verdict_good
                        : "refutes".equals(e.stance) ? R.color.verdict_bad : R.color.gray_text));
                ((TextView) row.findViewById(R.id.tvExcerpt)).setText(e.excerpt);
                row.setOnClickListener(v -> Links.open(this, e.url));
                details.addView(row);
            }
        }
        if (claim.statistics != null) {
            for (AnalysisResult.Statistic s : claim.statistics) {
                addHeader(details, getString(R.string.result_statistic));
                TextView t = paragraph(details, s.indicator_name + " (" + s.country + ") : " + Format.number(s.latest_value)
                        + " " + (s.unit == null ? "" : s.unit) + (s.latest_year != null ? " — " + s.latest_year : "")
                        + (s.claimed_value != null ? "\n" + getString(R.string.result_claimed, s.claimed_value) : "")
                        + (s.comment != null && !s.comment.isEmpty() ? "\n" + s.comment : "")
                        + "\n" + s.source_name);
                t.setOnClickListener(v -> Links.open(this, s.source_url));
            }
        }
        if (claim.reasoning != null && !claim.reasoning.isEmpty()) {
            addHeader(details, getString(R.string.result_reasoning));
            for (AnalysisResult.ReasoningTest test : claim.reasoning) {
                paragraph(details, "• " + test.label + " — " + reasoningLabel(test.outcome)
                        + (test.summary != null && !test.summary.isEmpty() ? "\n" + test.summary : "")
                        + (test.effect != null && !test.effect.isEmpty() ? "\n" + test.effect : ""));
            }
        }
        if (claim.contacts != null && !claim.contacts.isEmpty()) {
            addHeader(details, getString(R.string.result_contacts));
            for (OfficialContact contact : claim.contacts) {
                View row = ContactViews.inflate(details);
                ContactViews.bind(row, contact);
                details.addView(row);
            }
        }

        MaterialButton toggle = view.findViewById(R.id.btnToggleDetails);
        toggle.setOnClickListener(v -> {
            boolean show = details.getVisibility() != View.VISIBLE;
            details.setVisibility(show ? View.VISIBLE : View.GONE);
            toggle.setText(show ? R.string.result_hide_details : R.string.result_show_details);
        });
        // Vérification physique : un membre proche du lieu peut constater lui-même (mobile uniquement).
        View physical = view.findViewById(R.id.btnPhysical);
        physical.setVisibility(editable ? View.VISIBLE : View.GONE);
        physical.setOnClickListener(v -> startActivity(CreateVerificationActivity.forClaim(this, claim.text, id)));
        return view;
    }

    private String stanceLabel(String stance) {
        if ("supports".equals(stance)) return getString(R.string.stance_supports);
        if ("refutes".equals(stance)) return getString(R.string.stance_refutes);
        return getString(R.string.stance_context);
    }

    private String reasoningLabel(String outcome) {
        if (outcome == null) return "";
        switch (outcome) {
            case "refute": return getString(R.string.reasoning_refute);
            case "affaiblit": return getString(R.string.reasoning_weakens);
            case "compatible": return getString(R.string.reasoning_compatible);
            default: return getString(R.string.reasoning_inconclusive);
        }
    }

    private void addHeader(ViewGroup parent, String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextAppearance(R.style.TextAppearance_Hoe_SectionLabel);
        t.setPadding(0, dp(12), 0, dp(4));
        parent.addView(t);
    }

    private TextView paragraph(ViewGroup parent, String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextAppearance(R.style.TextAppearance_Hoe_Body);
        t.setPadding(0, dp(2), 0, dp(6));
        parent.addView(t);
        return t;
    }

    private void addList(ViewGroup parent, int title, List<String> items) {
        if (items == null || items.isEmpty()) return;
        addHeader(parent, getString(title));
        paragraph(parent, "• " + String.join("\n• ", items));
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density);
    }

    private void bindArticle(AnalysisResult.Article article) {
        cardArticle.setVisibility(article != null ? View.VISIBLE : View.GONE);
        boolean editable = analysis != null && analysis.editable;
        findViewById(R.id.layoutArticleActions).setVisibility(editable ? View.VISIBLE : View.GONE);
        if (article == null) return;
        tvArticleTitle.setText(article.title);
        tvArticleLead.setText(article.lead);
        tvArticleKeyPoints.setVisibility(article.key_points == null || article.key_points.isEmpty() ? View.GONE : View.VISIBLE);
        if (article.key_points != null) tvArticleKeyPoints.setText("• " + String.join("\n• ", article.key_points));
        tvArticleBody.setText(Format.plainMarkdown(article.body_markdown));
        StringBuilder sources = new StringBuilder();
        if (article.sources != null) {
            for (AnalysisResult.ArticleSource s : article.sources) {
                sources.append(s.n).append(". ").append(s.title).append(" — ").append(s.publisher).append('\n');
            }
        }
        tvArticleSources.setText(sources.toString().trim());
    }

    private String articleText() {
        AnalysisResult.Article a = analysis.result.article;
        StringBuilder text = new StringBuilder(a.title).append("\n\n").append(a.lead).append("\n\n")
                .append(Format.plainMarkdown(a.body_markdown));
        if (a.sources != null) {
            text.append("\n\n");
            for (AnalysisResult.ArticleSource s : a.sources) {
                text.append(s.n).append(". ").append(s.title).append(" — ").append(s.url).append('\n');
            }
        }
        return text.toString();
    }

    private void shareArticle() {
        if (analysis == null || analysis.result == null || analysis.result.article == null) return;
        Links.share(this, analysis.result.article.title, articleText());
    }

    private void regenerateArticle() {
        Toast.makeText(this, R.string.result_regenerating, Toast.LENGTH_SHORT).show();
        ApiClient.getApiService().regenerateArticle(id).enqueue(new ApiCallback<AnalysisResult.Article>(this) {
            @Override
            public void onSuccess(AnalysisResult.Article body) {
                analysis.result.article = body;
                bindArticle(body);
            }
        });
    }

    private void publish(String format) {
        new AlertDialog.Builder(this)
                .setMessage("article".equals(format) ? R.string.result_publish_article_confirm : R.string.result_publish_short_confirm)
                .setPositiveButton(R.string.publish, (d, w) -> {
                    Map<String, String> payload = new HashMap<>();
                    payload.put("format", format);
                    ApiClient.getApiService().publishArticle(id, payload).enqueue(new ApiCallback<Post>(this) {
                        @Override
                        public void onSuccess(Post body) {
                            Toast.makeText(ResultActivity.this, R.string.post_published, Toast.LENGTH_SHORT).show();
                            workspaceBound = false;
                            load();
                        }
                    });
                })
                .setNegativeButton(R.string.cancel, null).show();
    }

    private void saveWorkspace() {
        JsonObject patch = new JsonObject();
        String title = etTitle.getText() != null ? etTitle.getText().toString().trim() : "";
        if (!title.isEmpty()) patch.addProperty("title", title);
        patch.addProperty("notes", etNotes.getText() != null ? etNotes.getText().toString() : "");
        JsonArray tags = new JsonArray();
        String raw = etTags.getText() != null ? etTags.getText().toString() : "";
        for (String tag : raw.split(",")) if (!tag.trim().isEmpty()) tags.add(tag.trim());
        patch.add("tags", tags);
        patch.addProperty("workflow", WORKFLOWS[spWorkflow.getSelectedItemPosition()]);
        ApiClient.getApiService().updateAnalysis(id, patch).enqueue(new ApiCallback<AnalysisOut>(this) {
            @Override
            public void onSuccess(AnalysisOut body) {
                Toast.makeText(ResultActivity.this, R.string.saved, Toast.LENGTH_SHORT).show();
                workspaceBound = false;
                bind(body);
            }
        });
    }

    private void confirmDelete() {
        new AlertDialog.Builder(this).setMessage(R.string.result_delete_confirm)
                .setPositiveButton(R.string.delete, (d, w) -> ApiClient.getApiService().deleteAnalysis(id)
                        .enqueue(new ApiCallback<Void>(this) {
                            @Override
                            public void onSuccess(Void body) {
                                Toast.makeText(ResultActivity.this, R.string.result_deleted, Toast.LENGTH_SHORT).show();
                                finish();
                            }
                        }))
                .setNegativeButton(R.string.cancel, null).show();
    }
}
