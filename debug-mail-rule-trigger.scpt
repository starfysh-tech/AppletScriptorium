using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		-- Log file path
		set logPath to (POSIX path of (path to home folder)) & "Code/AppletScriptorium/mail-rule-trigger-debug.log"

		-- Create/append to log
		set logEntry to ""
		set logEntry to logEntry & "=== TRIGGER AT " & (do shell script "date '+%Y-%m-%d %H:%M:%S'") & " ===" & linefeed
		set logEntry to logEntry & "Rule name: " & name of theRule & linefeed
		set logEntry to logEntry & "Number of messages: " & (count of theMessages) & linefeed & linefeed

		-- Log each message
		repeat with msg in theMessages
			set logEntry to logEntry & "Message:" & linefeed
			try
				set logEntry to logEntry & "  From: " & (sender of msg) & linefeed
			end try
			try
				set logEntry to logEntry & "  Subject: " & (subject of msg) & linefeed
			end try
			try
				set logEntry to logEntry & "  Date: " & (date received of msg) & linefeed
			end try
			try
				set logEntry to logEntry & "  Message ID: " & (message id of msg) & linefeed
			end try
			try
				set logEntry to logEntry & "  Account: " & (name of (account of (mailbox of msg))) & linefeed
			end try
			try
				set logEntry to logEntry & "  Mailbox: " & (name of (mailbox of msg)) & linefeed
			end try
			set logEntry to logEntry & linefeed
		end repeat

		-- Write to log file
		do shell script "echo " & quoted form of logEntry & " >> " & quoted form of logPath

	end perform mail action with messages
end using terms from
