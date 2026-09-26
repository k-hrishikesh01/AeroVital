plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.aerovital.shared"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    implementation(libs.gson)
    testImplementation(libs.junit)
}
