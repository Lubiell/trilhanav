package io.github.lubiell.trilhanav;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(TrilhaNativePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
