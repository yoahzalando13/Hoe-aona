package com.hoeaona.mobile.api;

import android.content.Context;
import android.content.SharedPreferences;
import com.hoeaona.mobile.BuildConfig;
import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.util.concurrent.TimeUnit;

public class ApiClient {
    private static final String PREFS = "hoe_settings";
    private static final String KEY_SERVER = "server_url";
    /** Identifie l'application mobile : la vérification physique n'est servie qu'à elle. */
    public static final String CLIENT_HEADER = "X-Hoe-Client";

    private static Context appContext;
    private static String baseUrl;
    private static PersistentCookieJar cookieJar;
    private static OkHttpClient httpClient;
    private static ApiService apiService;

    public static void init(Context context) {
        appContext = context.getApplicationContext();
        cookieJar = new PersistentCookieJar(appContext);
        baseUrl = normalize(prefs().getString(KEY_SERVER, BuildConfig.API_BASE_URL));
    }

    private static SharedPreferences prefs() {
        return appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static String normalize(String url) {
        url = url.trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://" + url;
        return url.endsWith("/") ? url : url + "/";
    }

    public static String getServerUrl() {
        return baseUrl;
    }

    public static synchronized void setServerUrl(String url) {
        baseUrl = normalize(url);
        prefs().edit().putString(KEY_SERVER, baseUrl).apply();
        httpClient = null;
        apiService = null;
    }

    public static synchronized OkHttpClient getHttpClient() {
        if (httpClient == null) {
            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            // Jamais le corps des requêtes : il contient mots de passe et positions.
            logging.setLevel(BuildConfig.DEBUG ? HttpLoggingInterceptor.Level.BASIC : HttpLoggingInterceptor.Level.NONE);
            httpClient = new OkHttpClient.Builder()
                    .cookieJar(cookieJar)
                    .addInterceptor(chain -> chain.proceed(chain.request().newBuilder()
                            .header(CLIENT_HEADER, "android").build()))
                    .addInterceptor(logging)
                    .connectTimeout(20, TimeUnit.SECONDS)
                    .readTimeout(60, TimeUnit.SECONDS)
                    .writeTimeout(120, TimeUnit.SECONDS)
                    .build();
        }
        return httpClient;
    }

    public static synchronized ApiService getApiService() {
        if (apiService == null) {
            Retrofit retrofit = new Retrofit.Builder()
                    .baseUrl(baseUrl + "api/")
                    .client(getHttpClient())
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
            apiService = retrofit.create(ApiService.class);
        }
        return apiService;
    }

    /** Transforme un chemin renvoyé par l'API (« /api/posts/…/image ») en adresse complète. */
    public static String absolute(String path) {
        if (path == null) return null;
        if (path.startsWith("http://") || path.startsWith("https://")) return path;
        return baseUrl + (path.startsWith("/") ? path.substring(1) : path);
    }

    public static void clearSession() {
        cookieJar.clear();
    }
}
