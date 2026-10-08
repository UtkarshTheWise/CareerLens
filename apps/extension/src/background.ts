// Explicit action listener grants activeTab; automatic side-panel action behavior does not.
const configure = () =>
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: false })
    .catch(() => {});
chrome.runtime.onInstalled.addListener(() => void configure());
chrome.runtime.onStartup.addListener(() => void configure());
void configure();
chrome.action.onClicked.addListener((tab) => {
  // Call synchronously within the toolbar gesture; do not inspect or inject page contents here.
  if (tab.windowId !== undefined)
    void chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {});
});
