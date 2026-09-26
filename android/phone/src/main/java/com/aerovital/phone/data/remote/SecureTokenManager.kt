package com.aerovital.phone.data.remote

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SecureTokenManager(context: Context) : TokenManager {

    private val prefs: SharedPreferences = context.getSharedPreferences("auth_prefs", Context.MODE_PRIVATE)
    private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    init {
        if (!keyStore.containsAlias(KEY_ALIAS)) {
            val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
            val keyGenParameterSpec = KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build()
            keyGenerator.init(keyGenParameterSpec)
            keyGenerator.generateKey()
        }
    }

    private fun getSecretKey(): SecretKey {
        return keyStore.getKey(KEY_ALIAS, null) as SecretKey
    }

    override fun saveToken(token: String) {
        try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getSecretKey())
            val iv = cipher.iv
            val encrypted = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
            
            prefs.edit()
                .putString(PREF_IV, Base64.encodeToString(iv, Base64.DEFAULT))
                .putString(PREF_TOKEN, Base64.encodeToString(encrypted, Base64.DEFAULT))
                .apply()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun getToken(): String? {
        try {
            val ivString = prefs.getString(PREF_IV, null) ?: return null
            val tokenString = prefs.getString(PREF_TOKEN, null) ?: return null
            
            val iv = Base64.decode(ivString, Base64.DEFAULT)
            val encrypted = Base64.decode(tokenString, Base64.DEFAULT)
            
            val cipher = Cipher.getInstance(TRANSFORMATION)
            val spec = GCMParameterSpec(128, iv)
            cipher.init(Cipher.DECRYPT_MODE, getSecretKey(), spec)
            
            val decrypted = cipher.doFinal(encrypted)
            return String(decrypted, Charsets.UTF_8)
        } catch (e: Exception) {
            e.printStackTrace()
            return null
        }
    }

    override fun clearToken() {
        prefs.edit()
            .remove(PREF_IV)
            .remove(PREF_TOKEN)
            .apply()
    }

    companion object {
        private const val KEY_ALIAS = "auth_token_key"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val PREF_IV = "token_iv"
        private const val PREF_TOKEN = "encrypted_token"
    }
}
