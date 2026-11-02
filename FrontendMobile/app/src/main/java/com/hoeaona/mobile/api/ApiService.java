package com.hoeaona.mobile.api;

import com.hoeaona.mobile.model.*;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.http.*;

import java.util.List;
import java.util.Map;

public interface ApiService {

    @POST("auth/login")
    Call<User> login(@Body Map<String, String> credentials);

    @POST("auth/register")
    Call<User> register(@Body Map<String, String> payload);

    @GET("auth/me")
    Call<User> getMe();

    @POST("auth/logout")
    Call<Void> logout();

    @GET("auth/config")
    Call<AuthConfig> getAuthConfig();

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

    @GET("analyses/{id}")
    Call<AnalysisOut> getAnalysis(@Path("id") String id);

    @DELETE("analyses/{id}")
    Call<Void> deleteAnalysis(@Path("id") String id);

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

    @PUT("posts/{id}/like")
    Call<Post> likePost(@Path("id") String id);

    @DELETE("posts/{id}/like")
    Call<Post> unlikePost(@Path("id") String id);

    @GET("posts/{id}/comments")
    Call<List<Comment>> getComments(@Path("id") String id);

    @POST("posts/{id}/comments")
    Call<List<Comment>> addComment(@Path("id") String id, @Body Map<String, String> payload);

    @GET("sources")
    Call<List<OfficialSource>> listSources(
            @Query("q") String q,
            @Query("all") boolean all
    );

    @GET("settings")
    Call<Preferences> getSettings();

    @PUT("settings")
    Call<Preferences> saveSettings(@Body Preferences preferences);
}
