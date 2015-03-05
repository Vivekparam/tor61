// Usage: java FetchDriver serviceName

import java.io.BufferedReader;
import java.io.InputStreamReader;

class FetchDriver {

    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("Usage: java FetchDriver serviceName");
            System.exit(0);
        }
        fetch(args[0]);
    }

    public static void fetch(String name) {
        try {
            ProcessBuilder pb = new ProcessBuilder("python","fetch.py", name);
            //pb.inheritIO();
            Process p = pb.start();
            // read output, line by line
            BufferedReader in = new BufferedReader(new InputStreamReader(p.getInputStream()));
            String line;
            while ((line = in.readLine()) != null ) {
              System.out.println("Read: " + line);
            }
            //p.waitFor();
        }
        catch(Exception e) {
            e.printStackTrace();
        }
    }
}
