import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;
import java.io.File;
import java.nio.file.Files;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import java.util.Collections;

/** Assina o APK do TrilhaNav com a chave fixa (usar pelo assinar.sh): Signer entrada.apk saida.apk chave.p12 senha.txt.
 *  A senha é lida do arquivo e nunca impressa; no fim confere a assinatura e mostra o SHA-256 do certificado. */
public class Signer {
    public static void main(String[] a) throws Exception {
        char[] pw = new String(Files.readAllBytes(new File(a[3]).toPath()), "UTF-8").trim().toCharArray();
        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (java.io.FileInputStream in = new java.io.FileInputStream(a[2])) { ks.load(in, pw); }
        PrivateKey key = (PrivateKey) ks.getKey("trilhanav", pw);
        X509Certificate cert = (X509Certificate) ks.getCertificate("trilhanav");
        ApkSigner.SignerConfig sc = new ApkSigner.SignerConfig.Builder("trilhanav", key, Collections.singletonList(cert)).build();
        new ApkSigner.Builder(Collections.singletonList(sc)).setInputApk(new File(a[0])).setOutputApk(new File(a[1]))
            .setV1SigningEnabled(true).setV2SigningEnabled(true).setV3SigningEnabled(true)
            .setDebuggableApkPermitted(true).setLibraryPageAlignmentBytes(16384).build().sign();
        ApkVerifier.Result r = new ApkVerifier.Builder(new File(a[1])).build().verify();
        if (!r.isVerified()) { System.out.println("FALHOU: " + r.getErrors()); System.exit(1); }
        if (r.getSignerCertificates().size() != 1) { System.out.println("FALHOU: mais de um assinante"); System.exit(1); }
        X509Certificate c = r.getSignerCertificates().get(0);
        byte[] d = MessageDigest.getInstance("SHA-256").digest(c.getEncoded());
        StringBuilder h = new StringBuilder(); for (byte b : d) h.append(String.format("%02x", b));
        System.out.println("ok v1=" + r.isVerifiedUsingV1Scheme() + " v2=" + r.isVerifiedUsingV2Scheme() + " v3=" + r.isVerifiedUsingV3Scheme() + " cert=" + h);
    }
}
