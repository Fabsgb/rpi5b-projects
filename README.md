# rpi5b-projects

Personal automation and utility scripts, primarily for Linux and Raspberry Pi systems. Each script is independent and may have its own runtime requirements and configuration.

<details>
  <summary><b>DISCLAIMER</b></summary>
  ## ⚠️ Disclaimer & Liability Waiver

  > This repository and all scripts and contents contained herein are provided **strictly for educational, learning, and personal automation purposes only**.

  ### 📌 Important Notes

  * **No Warranty:** The code is provided *"as is"*, without warranty of any kind, express or implied, regarding its correctness, completeness, functionality, or timeliness.
  * **Full Personal Responsibility:** The use of these scripts is **entirely at your own risk**. You are solely responsible for how you deploy the code and what tools or platforms you interact with using it.
  * **Terms of Service (ToS):** Many platforms and websites have specific policies regarding automated access. It is your responsibility to ensure that your actions comply with any applicable terms.

  ### 🛡️ Limitation of Liability
  The authors or contributors of this repository assume **no liability whatsoever** for any direct or indirect damages, data loss, account bans, or other consequences arising from the use or operation of the scripts provided herein.
</details>

## Projects

| Path | Purpose |
| --- | --- |
| [`auto_report_f2b_email`](auto_report_f2b_email) | Looks up IP registration data and runs an email-report workflow for an IP address and log excerpt. |
| [`bigger_pics`](bigger_pics) | Upscales an image through the Bigger.pics website using browser automation. |
| [`crawl`](crawl) | Crawls a site, parses sitemaps, and can generate an HTML report with keyword or Ollama-assisted analysis. |
| [`get_perchance_infos`](get_perchance_infos) | Reads available image-generation styles, shapes, and image counts from Perchance. |
| [`image_api`](image_api) | FastAPI endpoint that runs the image generator and returns generated image data. |
| [`monitor_swap`](monitor_swap) | Monitors Linux swap usage and logs readings above its configured threshold. |
| [`perchance_image_generator`](perchance_image_generator) | Automates image generation through Perchance, with optional upscaling. |
| [`send_email`](send_email) | Interactive shell script for sending an email directly to the recipient's mail server. |
| [`update_time`](update_time) | Sets the system timezone and enables time synchronization. |
| [`my-libs/`](my-libs/) | Shared Python helpers for logging, text normalization, temporary paths, and browser automation. |

## Running

- Run scripts individually from the repository root with the interpreter indicated by their shebang. For example, `python3 ./crawl --help` shows the crawler's options.
- There is no shared dependency manifest; Python dependencies vary by script. Use a virtual environment and install only the dependencies needed by the script you plan to run.
- The Perchance browser scripts use Camoufox and are configured to connect through a proxy at `http://localhost:666`. Make sure that proxy is available or adjust the script configuration before running them.
- `auto_report_f2b_email` reads `SMTP_PASSWORD` from the environment (or a local `.env` file). Keep credentials private; `.env` is ignored by Git.
- `image_api` currently uses a fixed `SCRIPT_PATH` that may need to be changed for your checkout. Running it directly listens on `0.0.0.0:8000` and provides no authentication; do not expose it to an untrusted network.
- `monitor_swap` runs continuously and writes to `/home/server/swap.log` by default. Review its settings and log permissions before starting it.
- `update_time` requires root privileges and changes the host timezone and NTP setting.

## Safety

Only crawl or automate websites when you have permission, and follow their terms and access policies. The crawler includes path-discovery options; use them only on authorized targets. Review a script's configuration before running it, especially when it sends email, changes system settings, or starts a network service.

See [LICENSE](LICENSE) for licensing information.