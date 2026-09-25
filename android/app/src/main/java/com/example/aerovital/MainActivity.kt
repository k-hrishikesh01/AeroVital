package com.example.aerovital

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.Composable
import com.example.aerovital.ui.DashboardScreen
import com.example.aerovital.ui.ForgotPasswordScreen
import com.example.aerovital.ui.LoginScreen
import com.example.aerovital.ui.SignUpScreen
import com.example.aerovital.ui.theme.AeroVitalTheme


class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {

        super.onCreate(savedInstanceState)

        setContent {

            AeroVitalApp()
        }
    }
}


enum class AppScreen {

    LOGIN,
    SIGN_UP,
    FORGOT_PASSWORD,
    DASHBOARD
}


@Composable
fun AeroVitalApp() {

    var currentScreen by remember {
        mutableStateOf(AppScreen.LOGIN)
    }


    AeroVitalTheme {

        when (currentScreen) {

            /*
             * LOGIN
             */

            AppScreen.LOGIN -> {

                LoginScreen(

                    onLogin = { pilotId, password ->

                        /*
                         * Temporary login logic.
                         *
                         * Later this will call the backend.
                         */

                        currentScreen = AppScreen.DASHBOARD
                    },

                    onForgotPassword = {

                        currentScreen =
                            AppScreen.FORGOT_PASSWORD
                    },

                    onCreateAccount = {

                        currentScreen =
                            AppScreen.SIGN_UP
                    }
                )
            }


            /*
             * SIGN UP
             */

            AppScreen.SIGN_UP -> {

                SignUpScreen(

                    onBack = {

                        currentScreen =
                            AppScreen.LOGIN
                    },

                    onCreateAccount = { name, pilotId, password ->

                        /*
                         * Temporary behaviour.
                         *
                         * Later this will send
                         * account data to backend.
                         */

                        currentScreen =
                            AppScreen.LOGIN
                    }
                )
            }


            /*
             * FORGOT PASSWORD
             */

            AppScreen.FORGOT_PASSWORD -> {

                ForgotPasswordScreen(

                    onBack = {

                        currentScreen =
                            AppScreen.LOGIN
                    },

                    onResetPassword = { pilotId ->

                        /*
                         * Temporary behaviour.
                         *
                         * Backend integration
                         * will come later.
                         */

                        currentScreen =
                            AppScreen.LOGIN
                    }
                )
            }


            /*
             * DASHBOARD
             */

            AppScreen.DASHBOARD -> {

                DashboardScreen(

                    onMenuClick = {

                        /*
                         * Navigation drawer
                         * will be added later.
                         */

                    },

                    onProfileClick = {

                        /*
                         * Profile screen
                         * will be added later.
                         */
                    }
                )
            }
        }
    }
}