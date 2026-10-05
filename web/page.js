/* ==========================================================================
   Page script

   Five small jobs. Each one quietly does nothing when its part of the page
   is missing, and the page still reads fine with scripts turned off:

     1. count the days to Election Day in the banner;
     2. say how close the earliest registration deadline is (ask 1);
     3. share the ready-made message (ask 2) by text, email, the phone's
        share sheet or the clipboard;
     4. show only the steps for the way the reader plans to vote (ask 3);
     5. put Election Day in the reader's calendar.

   Nothing is stored and nothing is sent anywhere: the page has no trackers.
   ========================================================================== */

(function () {
  "use strict";

  /* ------------------------------------------------------------------------
     Shared helpers
     ------------------------------------------------------------------------ */

  var MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

  // Reads an ISO date ("2026-11-03") as midnight, local time, on that day,
  // so day counts follow the reader's own calendar rather than UTC.
  function parseLocalDate(isoDate) {
    var yearMonthDay = isoDate.split("-").map(Number);
    return new Date(yearMonthDay[0], yearMonthDay[1] - 1, yearMonthDay[2]);
  }

  // Whole days from one local midnight to another. Rounding absorbs the hour
  // gained or lost when daylight saving time ends in between.
  function wholeDaysBetween(earlierDay, laterDay) {
    return Math.round((laterDay - earlierDay) / MILLISECONDS_PER_DAY);
  }

  // A date as the eight digits calendars expect: 2026-11-03 becomes 20261103.
  function calendarDate(day) {
    var month = String(day.getMonth() + 1).padStart(2, "0");
    var dayOfMonth = String(day.getDate()).padStart(2, "0");
    return day.getFullYear() + month + dayOfMonth;
  }

  // The address to share: the canonical link once the page is hosted,
  // otherwise wherever the reader found it.
  function pageAddress() {
    var canonicalLink = document.querySelector('link[rel="canonical"]');
    if (canonicalLink && canonicalLink.href) {
      return canonicalLink.href;
    }
    return window.location.href.split("#")[0];
  }

  /* ------------------------------------------------------------------------
     1. Countdown to Election Day
     ------------------------------------------------------------------------ */

  function showCountdown() {
    var countdown = document.querySelector("[data-countdown]");
    if (!countdown) {
      return;
    }

    var electionDay = parseLocalDate(countdown.getAttribute("data-election-day"));
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var daysToGo = wholeDaysBetween(today, electionDay);

    if (daysToGo > 1) {
      countdown.textContent = daysToGo + " days to go";
    } else if (daysToGo === 1) {
      countdown.textContent = "Tomorrow!";
    } else if (daysToGo === 0) {
      countdown.textContent = "Today. Go vote!";
    }
    // After Election Day the banner simply keeps the date.
  }

  /* ------------------------------------------------------------------------
     2. How close the earliest registration deadline is
     ------------------------------------------------------------------------ */

  // Federal law lets a state close registration no earlier than a set number
  // of days before Election Day (30, from facts.py). This counts down to that
  // day, the earliest any state may close, and afterwards says it has passed.
  function showRegistrationCountdown() {
    var notice = document.querySelector("[data-registration-countdown]");
    if (!notice) {
      return;
    }

    var electionDay = parseLocalDate(notice.getAttribute("data-election-day"));
    var daysBeforeElection = Number(notice.getAttribute("data-earliest-close-days"));
    var earliestClose = new Date(
      electionDay.getFullYear(),
      electionDay.getMonth(),
      electionDay.getDate() - daysBeforeElection
    );
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var daysLeft = wholeDaysBetween(today, earliestClose);

    if (daysLeft > 1) {
      notice.textContent = "The earliest deadline federal law allows is " + daysLeft + " days away.";
    } else if (daysLeft === 1) {
      notice.textContent = "The earliest deadline federal law allows is tomorrow.";
    } else if (daysLeft === 0) {
      notice.textContent = "The earliest deadline federal law allows is today.";
    } else {
      notice.textContent =
        "The earliest deadlines have passed. Check your state's, and remember that some states register you when you vote.";
    }
    notice.hidden = false;
  }

  /* ------------------------------------------------------------------------
     3. Sharing the ready-made message
     ------------------------------------------------------------------------ */

  // Copies text to the clipboard. Browsers only allow the modern clipboard
  // on secure pages, so a page opened from a file falls back to the old way:
  // select a hidden copy of the text and ask the browser to copy it.
  function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var hiddenCopy = document.createElement("textarea");
      hiddenCopy.value = text;
      hiddenCopy.setAttribute("readonly", "");
      hiddenCopy.style.position = "fixed";
      hiddenCopy.style.opacity = "0";
      document.body.appendChild(hiddenCopy);
      hiddenCopy.select();
      var copied = false;
      try {
        copied = document.execCommand("copy");
      } catch (error) {
        copied = false;
      }
      document.body.removeChild(hiddenCopy);
      if (copied) {
        resolve();
      } else {
        reject();
      }
    });
  }

  function setUpSharing() {
    var shareBox = document.querySelector("[data-share-box]");
    if (!shareBox) {
      return;
    }

    var messageField = shareBox.querySelector("textarea");
    var statusLine = shareBox.querySelector("[data-share-status]");
    var emailSubject = shareBox.getAttribute("data-email-subject") || document.title;
    var clearStatusTimer = null;

    // The message as it reads now (the reader may have edited it), with the
    // page's address on the end so whoever receives it can act on it.
    function messageWithLink() {
      return messageField.value.trim() + "\n\n" + pageAddress();
    }

    function showStatus(text) {
      if (!statusLine) {
        return;
      }
      statusLine.textContent = text;
      window.clearTimeout(clearStatusTimer);
      clearStatusTimer = window.setTimeout(function () {
        statusLine.textContent = "";
      }, 5000);
    }

    function shareBy(shareMethod) {
      if (shareMethod === "device") {
        navigator
          .share({ title: document.title, text: messageField.value.trim(), url: pageAddress() })
          .catch(function () {
            // The reader closed the share sheet; nothing to do.
          });
      } else if (shareMethod === "text") {
        // "sms:?&body=" is the one form that both iPhones and Android phones accept.
        window.location.href = "sms:?&body=" + encodeURIComponent(messageWithLink());
      } else if (shareMethod === "email") {
        window.location.href =
          "mailto:?subject=" + encodeURIComponent(emailSubject) +
          "&body=" + encodeURIComponent(messageWithLink());
      } else if (shareMethod === "copy") {
        copyToClipboard(messageWithLink()).then(
          function () {
            showStatus("Copied. Paste it into any app.");
          },
          function () {
            showStatus("Your browser blocked copying. Select the message and copy it yourself.");
          }
        );
      }
    }

    // The buttons start hidden, because none of them works without this
    // script. The phone share sheet stays hidden where the browser lacks it.
    var shareButtons = shareBox.querySelectorAll("[data-share]");
    Array.prototype.forEach.call(shareButtons, function (button) {
      var shareMethod = button.getAttribute("data-share");
      if (shareMethod === "device" && typeof navigator.share !== "function") {
        return;
      }
      button.hidden = false;
      button.addEventListener("click", function () {
        shareBy(shareMethod);
      });
    });
  }

  /* ------------------------------------------------------------------------
     4. The voting plan: show the steps for the chosen way to vote
     ------------------------------------------------------------------------ */

  function setUpVotingPlan() {
    var planPicker = document.querySelector("[data-plan-picker]");
    if (!planPicker) {
      return;
    }

    var votingMethodChoices = planPicker.querySelectorAll('input[name="voting-method"]');
    var stepPanels = document.querySelectorAll("[data-plan-steps]");

    // With scripts off every panel shows; with them on, only the chosen one.
    function showStepsFor(votingMethod) {
      Array.prototype.forEach.call(stepPanels, function (panel) {
        panel.hidden = panel.getAttribute("data-plan-steps") !== votingMethod;
      });
    }

    Array.prototype.forEach.call(votingMethodChoices, function (choice) {
      choice.addEventListener("change", function () {
        showStepsFor(choice.value);
      });
    });

    var checkedChoice = planPicker.querySelector('input[name="voting-method"]:checked');
    showStepsFor(checkedChoice ? checkedChoice.value : null);
  }

  /* ------------------------------------------------------------------------
     5. Election Day in the reader's calendar
     ------------------------------------------------------------------------ */

  // Escapes text for a calendar file, where commas, semicolons and
  // backslashes are special and line breaks are written as \n.
  function calendarText(text) {
    return text
      .replace(/\\/g, "\\\\")
      .replace(/([,;])/g, "\\$1")
      .replace(/\r?\n/g, "\\n");
  }

  function setUpCalendarButtons() {
    var calendarBox = document.querySelector("[data-calendar]");
    if (!calendarBox) {
      return;
    }

    var electionDay = parseLocalDate(calendarBox.getAttribute("data-election-day"));
    var dayAfterElection = new Date(
      electionDay.getFullYear(),
      electionDay.getMonth(),
      electionDay.getDate() + 1
    );
    var eventTitle = calendarBox.getAttribute("data-event-title");
    var eventDetails = calendarBox.getAttribute("data-event-details") + "\n" + pageAddress();

    // Google Calendar: a link that opens a filled-in "new event" form.
    var googleCalendarLink = calendarBox.querySelector("[data-calendar-google]");
    if (googleCalendarLink) {
      googleCalendarLink.href =
        "https://calendar.google.com/calendar/render?action=TEMPLATE" +
        "&text=" + encodeURIComponent(eventTitle) +
        "&dates=" + calendarDate(electionDay) + "/" + calendarDate(dayAfterElection) +
        "&details=" + encodeURIComponent(eventDetails);
      googleCalendarLink.hidden = false;
    }

    // Apple Calendar, Outlook and the rest: a small .ics file made on the spot.
    // It is an all-day event with a reminder at 7 a.m. on the day.
    var calendarFileButton = calendarBox.querySelector("[data-calendar-file]");
    if (calendarFileButton) {
      calendarFileButton.hidden = false;
      calendarFileButton.addEventListener("click", function () {
        var createdAt = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
        var calendarFileLines = [
          "BEGIN:VCALENDAR",
          "VERSION:2.0",
          "PRODID:-//USDemCongress2026//Election Day reminder//EN",
          "CALSCALE:GREGORIAN",
          "BEGIN:VEVENT",
          "UID:election-day-" + calendarDate(electionDay) + "@usdemcongress2026",
          "DTSTAMP:" + createdAt,
          "DTSTART;VALUE=DATE:" + calendarDate(electionDay),
          "DTEND;VALUE=DATE:" + calendarDate(dayAfterElection),
          "SUMMARY:" + calendarText(eventTitle),
          "DESCRIPTION:" + calendarText(eventDetails),
          "BEGIN:VALARM",
          "TRIGGER:PT7H",
          "ACTION:DISPLAY",
          "DESCRIPTION:" + calendarText(eventTitle),
          "END:VALARM",
          "END:VEVENT",
          "END:VCALENDAR"
        ];
        var calendarFile = new Blob([calendarFileLines.join("\r\n") + "\r\n"], {
          type: "text/calendar;charset=utf-8"
        });
        var downloadLink = document.createElement("a");
        downloadLink.href = URL.createObjectURL(calendarFile);
        downloadLink.download = "election-day-" + calendarDate(electionDay) + ".ics";
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        window.setTimeout(function () {
          URL.revokeObjectURL(downloadLink.href);
        }, 10000);
      });
    }
  }

  /* ------------------------------------------------------------------------
     Start
     ------------------------------------------------------------------------ */

  showCountdown();
  showRegistrationCountdown();
  setUpSharing();
  setUpVotingPlan();
  setUpCalendarButtons();
})();
