package io.github.lubiell.trilhanav;

import android.os.Bundle;
import android.view.WindowManager;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(TrilhaNativePlugin.class);
        super.onCreate(savedInstanceState);
        // navegação no guidão: a tela não apaga sozinha enquanto o app está aberto
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        // Voltar: fecha a janela aberta no app; sem janela, manda o app para segundo plano (não fecha: GPS e gravação continuam)
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (getBridge() == null || getBridge().getWebView() == null) { moveTaskToBack(true); return; }
                getBridge().getWebView().evaluateJavascript("(window.tnBack&&window.tnBack())?1:0", r -> {
                    if (!"1".equals(r)) moveTaskToBack(true);
                });
            }
        });
    }
}
