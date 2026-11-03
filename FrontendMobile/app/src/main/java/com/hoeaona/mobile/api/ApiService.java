package com.hoeaona.mobile.api;

import com.google.gson.JsonObject;
import com.hoeaona.mobile.model.*;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.*;

import java.util.List;
import java.util.Map;

public interface ApiService {

    // ---------- comptes ----------
    @GET("auth/config")
    Call<AuthConfig> getAuthConfig();

    @POST("auth/login")
    Call<User> login(@Body Map<String, String> credentials);

    @POST("auth/register")
    Call<User> register(@Body Map<String, String> payload);

    @GET("auth/me")
    Call<User> getMe();

    @PATCH("auth/me")
    Call<User> updateMe(@Body Map<String, String> patch);

    @POST("auth/password")
    Call<Void> changePassword(@Body Map<String, String> payload);

    @POST("auth/logout")
    Call<Void> logout();

    @GET("users/{id}")
    Call<PublicUser> getProfile(@Path("id") String id);

    // ---------- analyses ----------
    @Multipart
    @POST("analyses")
    Call<AnalysisOut> createAnalysis(
            @Part("text") RequestBody text,
            @Part("urls") RequestBody urls,
            @Part List<MultipartBody.Part> files
    );

    @GET("analyses")
    Call<AnalysisPage> listAnalyses(
            @Query("q") String q,
            @Query("verdict") String verdict,
            @Query("workflow") String workflow,
            @Query("tag") String tag,
            @Query("limit") int limit,
            @Query("offset") int offset
    );

    @GET("analyses/stats")
    Call<AnalysisStats> analysisStats();

    @GET("analyses/export.csv")
    Call<ResponseBody> exportCsv();

    @GET("analyses/{id}")
    Call<AnalysisOut> getAnalysis(@Path("id") String id);

    @PATCH("analyses/{id}")
    Call<AnalysisOut> updateAnalysis(@Path("id") String id, @Body JsonObject patch);

    @DELETE("analyses/{id}")
    Call<Void> deleteAnalysis(@Path("id") String id);

    @POST("analyses/{id}/article")
    Call<AnalysisResult.Article> regenerateArticle(@Path("id") String id);

    @POST("analyses/{id}/publish")
    Call<Post> publishArticle(@Path("id") String id, @Body Map<String, String> payload);

    // ---------- fil média ----------
    @GET("posts")
    Call<PostPage> listPosts(
            @Query("q") String q,
            @Query("author") String author,
            @Query("limit") int limit,
            @Query("offset") int offset
    );

    @Multipart
    @POST("posts")
    Call<Post> createPost(
            @Part("body") RequestBody body,
            @Part("analysis_id") RequestBody analysisId,
            @Part MultipartBody.Part image
    );

    @GET("posts/{id}")
    Call<Post> getPost(@Path("id") String id);

    @PATCH("posts/{id}")
    Call<Post> editPost(@Path("id") String id, @Body Map<String, String> payload);

    @DELETE("posts/{id}")
    Call<Void> deletePost(@Path("id") String id);

    @PUT("posts/{id}/like")
    Call<Post> likePost(@Path("id") String id);

    @DELETE("posts/{id}/like")
    Call<Post> unlikePost(@Path("id") String id);

    @GET("posts/{id}/comments")
    Call<List<Comment>> getComments(@Path("id") String id);

    @POST("posts/{id}/comments")
    Call<List<Comment>> addComment(@Path("id") String id, @Body Map<String, String> payload);

    @DELETE("posts/{id}/comments/{commentId}")
    Call<Void> deleteComment(@Path("id") String id, @Path("commentId") String commentId);

    // ---------- annuaire, statistiques, paramètres ----------
    @GET("sources")
    Call<List<OfficialContact>> listSources(
            @Query("q") String q,
            @Query("all") boolean all
    );

    @GET("stats/madagascar")
    Call<List<StatSeries>> statsMadagascar();

    @GET("stats/activity")
    Call<PlatformActivity> statsActivity();

    @GET("stats/compare")
    Call<List<StatSeries>> statsCompare(@Query("indicator") String indicator);

    @GET("settings")
    Call<Preferences> getSettings();

    @PUT("settings")
    Call<Preferences> saveSettings(@Body Preferences preferences);

    @GET("health")
    Call<Health> health();

    // ---------- administration ----------
    @GET("admin/stats")
    Call<PlatformStats> adminStats();

    @GET("admin/users")
    Call<List<User>> adminUsers(@Query("q") String q);

    @PATCH("admin/users/{id}")
    Call<User> adminUpdateUser(@Path("id") String id, @Body JsonObject patch);

    @GET("admin/posts")
    Call<PostPage> adminPosts(@Query("q") String q, @Query("limit") int limit, @Query("offset") int offset);

    @PUT("admin/posts/{id}/hidden")
    Call<Post> hidePost(@Path("id") String id);

    @DELETE("admin/posts/{id}/hidden")
    Call<Post> unhidePost(@Path("id") String id);

    // ---------- vérification physique (mobile uniquement) ----------
    @GET("verifications/location")
    Call<JsonObject> locationStatus();

    @PUT("verifications/location")
    Call<Void> updateLocation(@Body Map<String, Double> position);

    @DELETE("verifications/location")
    Call<Void> stopSharingLocation();

    @POST("verifications")
    Call<Verification> createVerification(@Body JsonObject payload);

    @GET("verifications/nearby")
    Call<List<Verification>> nearbyVerifications();

    @GET("verifications/mine")
    Call<List<Verification>> myVerifications();

    @GET("verifications/assigned")
    Call<List<Verification>> assignedVerifications();

    @GET("verifications/{id}")
    Call<Verification> getVerification(@Path("id") String id);

    @POST("verifications/{id}/accept")
    Call<Verification> acceptVerification(@Path("id") String id);

    @POST("verifications/{id}/decline")
    Call<Void> declineVerification(@Path("id") String id);

    @POST("verifications/{id}/release")
    Call<Verification> releaseVerification(@Path("id") String id);

    @POST("verifications/{id}/cancel")
    Call<Verification> cancelVerification(@Path("id") String id);

    @POST("verifications/{id}/capture")
    Call<JsonObject> captureToken(@Path("id") String id);

    /** Constat certifié : jeton de prise de vue, position au moment du constat (jamais conservée). */
    @Multipart
    @POST("verifications/{id}/report")
    Call<Verification> reportVerification(
            @Path("id") String id,
            @PartMap Map<String, RequestBody> fields,
            @Part MultipartBody.Part photo
    );

    @POST("verifications/{id}/dispute")
    Call<Verification> disputeVerification(@Path("id") String id);

    @GET("verifications/notifications")
    Call<List<AppNotification>> notifications(@Query("undelivered") boolean undelivered);

    @POST("verifications/notifications/read")
    Call<Void> markNotificationsRead(@Body JsonObject payload);
}
