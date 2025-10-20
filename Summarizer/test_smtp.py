"""SMTP Test Script for Gmail App Password Authentication.

This script tests Gmail SMTP configuration by sending an existing .eml file.

Setup:
1. Generate a Gmail App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password

2. Set environment variables:
   export GMAIL_SMTP_USER=your-email@gmail.com
   export GMAIL_APP_PASSWORD=your-16-char-app-password
   export GMAIL_SMTP_HOST=smtp.gmail.com
   export GMAIL_SMTP_PORT=587

3. Run the test:
   python3 -m Summarizer.test_smtp --eml-file path/to/digest.eml --to recipient@example.com

The script will:
- Read the .eml file from disk
- Connect to Gmail SMTP with STARTTLS
- Authenticate using your app password
- Send the email to the specified recipient
- Log all steps with INFO level messages
"""
from __future__ import annotations

import argparse
import email
import logging
import os
import smtplib
import sys
from pathlib import Path


def setup_logging() -> None:
    """Configure logging for SMTP test."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


def load_eml_file(eml_path: Path) -> email.message.Message:
    """Load and parse .eml file from disk.

    Args:
        eml_path: Path to .eml file

    Returns:
        Parsed email message

    Raises:
        FileNotFoundError: If .eml file doesn't exist
        ValueError: If file cannot be parsed as email
    """
    if not eml_path.exists():
        raise FileNotFoundError(f"EML file not found: {eml_path}")

    logging.info("Reading EML file: %s", eml_path)

    with open(eml_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        msg = email.message_from_string(content)
    except Exception as exc:
        raise ValueError(f"Failed to parse EML file: {exc}")

    logging.info("EML file loaded successfully (%d bytes)", len(content))
    return msg


def get_smtp_config() -> dict[str, str]:
    """Load SMTP configuration from environment variables.

    Returns:
        Dictionary with SMTP config (user, password, host, port)

    Raises:
        ValueError: If required environment variables are missing
    """
    config = {
        "user": os.environ.get("GMAIL_SMTP_USER"),
        "password": os.environ.get("GMAIL_APP_PASSWORD"),
        "host": os.environ.get("GMAIL_SMTP_HOST", "smtp.gmail.com"),
        "port": os.environ.get("GMAIL_SMTP_PORT", "587"),
    }

    missing = [key for key, value in config.items() if not value or key == "password" and not config["password"]]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(f'GMAIL_SMTP_{k.upper()}' for k in missing)}\n"
            f"See script docstring for setup instructions."
        )

    # Validate port is numeric
    try:
        config["port"] = str(int(config["port"]))
    except ValueError:
        raise ValueError(f"GMAIL_SMTP_PORT must be numeric, got: {config['port']}")

    logging.info("SMTP config loaded: user=%s, host=%s, port=%s", config["user"], config["host"], config["port"])
    return config


def send_email_via_smtp(msg: email.message.Message, recipient: str, config: dict[str, str]) -> None:
    """Send email via Gmail SMTP with STARTTLS.

    Args:
        msg: Parsed email message
        recipient: Recipient email address
        config: SMTP configuration dictionary

    Raises:
        smtplib.SMTPException: On SMTP errors (connection, auth, send)
        ConnectionError: On network connection failures
    """
    from_addr = msg.get("From", config["user"])
    to_addr = recipient

    logging.info("Connecting to SMTP server: %s:%s", config["host"], config["port"])

    try:
        with smtplib.SMTP(config["host"], int(config["port"]), timeout=30) as server:
            server.set_debuglevel(0)  # Set to 1 for verbose SMTP protocol logs

            logging.info("Starting TLS encryption")
            server.starttls()

            logging.info("Authenticating as: %s", config["user"])
            try:
                server.login(config["user"], config["password"])
            except smtplib.SMTPAuthenticationError as exc:
                raise smtplib.SMTPAuthenticationError(
                    exc.smtp_code,
                    f"Authentication failed. Check GMAIL_APP_PASSWORD (use app password, not account password): {exc.smtp_error.decode()}"
                )

            logging.info("Sending email to: %s", to_addr)
            server.sendmail(from_addr, [to_addr], msg.as_string())

            logging.info("Email sent successfully!")

    except smtplib.SMTPConnectError as exc:
        raise ConnectionError(f"Failed to connect to SMTP server: {exc}")
    except smtplib.SMTPServerDisconnected as exc:
        raise ConnectionError(f"SMTP server disconnected unexpectedly: {exc}")
    except smtplib.SMTPException as exc:
        raise smtplib.SMTPException(f"SMTP error: {exc}")


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Gmail SMTP by sending an existing .eml file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--eml-file",
        required=True,
        type=Path,
        help="Path to .eml file to send",
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Recipient email address",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Main entry point for SMTP test script."""
    setup_logging()

    try:
        args = parse_args(argv)

        # Load SMTP configuration
        config = get_smtp_config()

        # Load .eml file
        msg = load_eml_file(args.eml_file)

        # Send email
        send_email_via_smtp(msg, args.to, config)

        logging.info("SMTP test completed successfully!")
        return 0

    except FileNotFoundError as exc:
        logging.error("File error: %s", exc)
        return 1
    except ValueError as exc:
        logging.error("Configuration error: %s", exc)
        return 1
    except (smtplib.SMTPException, ConnectionError) as exc:
        logging.error("SMTP error: %s", exc)
        return 1
    except Exception as exc:
        logging.error("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
