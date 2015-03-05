// Usage: java RegClientDriver
class RegClientDriver {

    // Change to your agent here
    public static final String PORT = "12345";
    public static final String NAME = "YOUR_AGENT_NAME";
    public static final String DATA = "12345";

    public static void main(String[] args) {
        register(PORT, NAME, DATA);
        while (true) {
          try {
            Thread.sleep(3000);
          } catch (Exception e) {
          }
          System.out.println("I'm still here");
        }
    }

    public static void register(String port, String name, String data) {
        try {
            ProcessBuilder pb = new ProcessBuilder("python","registration_client.py", port, name, data);
            pb.inheritIO();
            Process p = pb.start();
        }
        catch(Exception e) {
            e.printStackTrace();
        }
    }
}
