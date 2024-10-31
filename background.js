'use strict';

const isEdge = Boolean(navigator.userAgent.match(/Edg/));
const listener = isEdge ? 'http://localhost:62337/' : 'http://localhost:61337/';
let refreshInt;

// // 
// Check bookmarks and gather tab data
function refresh() {
	closeBookmark();

	chrome.windows.getLastFocused({}, (lastFocused) => {
		chrome.tabs.query({}, (tabs) => {
			chrome.windows.getAll((windows) => {
				const isBrowserActive = windows.some((window) => window.focused);

				for (const tab of tabs) {
					tab.browserActive = isBrowserActive;
					tab.active = tab.active && tab.windowId == lastFocused.id;
				}

				const data = JSON.stringify(tabs);
				sendArrayData("sendTabs", data);
			});
		});
	});
}

// //
// Schedule refresh every second
function scheduleRefresh() {
  if (refreshInt) {
    clearInterval(refreshInt);
  }
  console.debug("Scheduling refresh");
  refreshInt = setInterval(refresh, 1000);
}

// //
// find previously created bookmarklets and remove those as well
function closeBookmark() {
	chrome.bookmarks.search('javascript:', function(results) {
		for (const result of results) {
			if (result.url && result.url.match(/^javascript:/i)) {
        console.debug("Removing bookmarklet: " + result.url);
				chrome.bookmarks.remove(result.id);
			}
		}
	});
}

// remove immediately upon creation
// we are preventing the anti tab-close bookmarlet found here:
// https://sites.google.com/view/rbsug/bookmarklets
chrome.bookmarks.onCreated.addListener((_id, bookmark) => {
  if (bookmark.url && bookmark.url.match(/^javascript:/i)) {
    console.debug("Removing bookmarklet: " + bookmark.url);
    chrome.bookmarks.remove(bookmark.id);
  }
});

// //
// Send tab data to listener
function sendArrayData(action, data) {
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,HEAD,OPTIONS,POST,PUT',
      'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization'
    },
    body: "{\"action\" : \"" + action + "\", \"data\": " + data + "}"
  };

  fetch(listener, options)
    .then(async (response) => {
      const jResp = await response.json();

      switch (jResp.command) {
        case "closeTabWithId":
          console.debug("Closing tab with id: " + jResp.data)
          chrome.tabs.remove(jResp.data, () => {});
          break;

        case "focusTab":
          console.debug("Focusing tab with id: " + jResp.data)
          chrome.tabs.get(jResp.data, (tab) => {
            chrome.tabs.highlight({'tabs': tab.index}, () => {});
          });
          break;

        case "newTab":
          console.debug("Creating new tab with url: " + jResp.data)
          chrome.tabs.create({url: jResp.data}, function() {});
          break;

        case "updateTab":
          console.debug("Updating tab with id: " + jResp.data + " to url: " + jResp.data2)
          chrome.tabs.update(jResp.data, {url: jResp.data2}, function() {});
          break;
        }
    }).catch((error) => {
      console.log(error);
    });
}

// //
// Alarm to keep background script running
chrome.alarms.create('wake', { delayInMinutes: 1, periodInMinutes: 1});
chrome.alarms.onAlarm.addListener(function(alarm) {
  if (alarm.name === 'wake') {
    scheduleRefresh();
  }
});
scheduleRefresh();
