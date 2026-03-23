"use client";

import { useCallback, useState } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

import iconsData from "@/app/components/icons/icons.json";
import { useMeetingChat } from "@/app/lib/meeting/use-meeting-chat";
import useRaisedHands from "@/app/lib/meeting/use-raised-hands";

import ChatOverlay from "../chat/chat-overlay";
import GalleryLayout from "../layout/gallery-layout";
import ScreenShareLayout from "../layout/screen-share-layout";
import ShareMeetingModal from "../modals/share-meeting-modal";
import ParticipantsOverlay from "../participants/participants-overlay";
import RaisedHandsModal from "../participants/raised-hands-modal";
import TranscriptPanel from "../transcript/transcript-panel";
import MeetingControls from "../toolbar/meeting-controls";

const MeetingRoomContent = ({
  showAssistant,
  setShowAssistant,
  isHost,
  setCurrentHostId,
  pendingCount,
  onOpenWaitingRoom,
  onOpenParticipants,
  onCloseParticipants,
  participantsOpen,
  currentUserId,
  onLeave,
  callId,
  jwt,
  hasLeftRef,
  transcripts = [],
  transcriptConnected = false,
  transcriptReconnecting = false,
  transcriptConnectionError = null,
  isTranscriptOpen = false,
  onToggleTranscript,
  onCloseTranscript,
  isLeaving = false,
  isEnding = false,
  onStartLeaving,
  onStartEnding,
  resetExitState,
}) => {
  const { useParticipants, useHasOngoingScreenShare } = useCallStateHooks();
  const participants = useParticipants() ?? [];
  const participantCount = participants.length;
  const hasScreenShare = useHasOngoingScreenShare();

  const {
    raisedHandUserIds,
    raisedHandCount,
    raiseHand,
    lowerHand,
    lowerHandForUser,
    isHandRaised,
  } = useRaisedHands(currentUserId);

  const [showRaisedHandsModal, setShowRaisedHandsModal] = useState(false);
  const [showLeaveConfirmModal, setShowLeaveConfirmModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const {
    messages,
    connected,
    reconnecting,
    connectionError,
    sendMessage,
    unreadCount,
    markChatRead,
    removeMessageByClientId,
  } = useMeetingChat(callId, jwt, chatOpen, setCurrentHostId);

  const handleLeave = useCallback(() => {
    setShowRaisedHandsModal(false);
    setShowLeaveConfirmModal(false);
    lowerHand();
    onLeave?.();
  }, [onLeave, lowerHand]);

  const handleOpenChat = useCallback(() => {
    setChatOpen(true);
    markChatRead();
  }, [markChatRead]);

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
  }, []);

  const onEndMeeting = useCallback(async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl || !callId || !jwt) return false;
    try {
      const res = await fetch(`${apiUrl}/meetings/${callId}/end`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}` },
      });
      return res.ok;
    } catch {
      return false;
    }
  }, [callId, jwt]);

  const handleOpenRaisedHandsModal = useCallback(() => {
    setShowRaisedHandsModal(true);
  }, []);

  const handleCloseRaisedHandsModal = useCallback(() => {
    setShowRaisedHandsModal(false);
  }, []);

  const handleOpenShare = useCallback(() => {
    setShowShareModal(true);
  }, []);

  const handleCloseShareModal = useCallback(() => {
    setShowShareModal(false);
  }, []);

  const handleShowLeaveConfirmModal = useCallback(() => {
    setShowLeaveConfirmModal(true);
  }, []);

  const handleToggleAssistant = useCallback(async () => {
    const next = !showAssistant;
    setShowAssistant(next);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl && callId && jwt) {
      try {
        await fetch(`${apiUrl}/meetings/${callId}/assistant-preference`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
          },
          body: JSON.stringify({ enabled: next }),
        });
      } catch (err) {
        console.error("Assistant preference update failed:", err);
      }
    }
  }, [showAssistant, setShowAssistant, callId, jwt]);

  return (
    <div className="flex flex-col w-full h-full overflow-hidden bg-[#020617]">
      <div className="flex-1 flex flex-col px-2 py-2 sm:px-4 sm:py-4 md:px-6 md:py-4 lg:px-10 lg:py-6 min-h-0 overflow-hidden">
        {hasScreenShare ? (
          <ScreenShareLayout
            showAssistant={showAssistant}
            currentUserId={currentUserId}
            isHost={isHost}
            raisedHandUserIds={raisedHandUserIds}
            callId={callId}
            hasLeftRef={hasLeftRef}
            jwt={jwt}
          />
        ) : (
          <GalleryLayout
            showAssistant={showAssistant}
            currentUserId={currentUserId}
            isHost={isHost}
            raisedHandUserIds={raisedHandUserIds}
            callId={callId}
            hasLeftRef={hasLeftRef}
            jwt={jwt}
          />
        )}
      </div>

      <div className="flex justify-center items-center shrink-0 pb-1 sm:pb-2">
        <div className="w-full bg-[#020617] px-2 py-1.5 sm:px-4 sm:py-1.5 md:px-6 md:py-2 border-t border-slate-800/80 flex items-center gap-1.5 sm:gap-2 md:gap-3 flex-wrap justify-center">
          <button
            onClick={handleToggleAssistant}
            className={`flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors ${
              showAssistant
                ? "bg-green-500 hover:bg-green-600 text-white"
                : "bg-gray-700 hover:bg-gray-600 text-gray-300"
            }`}
            title={
              showAssistant
                ? "Assistant on (click to turn off)"
                : "Assistant off (click to turn on, then say Hey Assistant)"
            }
          >
            <span
              className="w-4 h-4 sm:w-5 sm:h-5"
              dangerouslySetInnerHTML={{ __html: iconsData.robot }}
            />
          </button>

          <MeetingControls
            onLeave={handleLeave}
            onOpenParticipants={onOpenParticipants}
            participantCount={participantCount}
            isHost={isHost}
            onEndMeeting={onEndMeeting}
            raisedHandCount={raisedHandCount}
            onOpenRaisedHands={handleOpenRaisedHandsModal}
            onRaiseHand={raiseHand}
            onLowerHand={lowerHand}
            isHandRaised={isHandRaised}
            onLeaveClick={isHost ? handleShowLeaveConfirmModal : undefined}
            showLeaveConfirmModal={showLeaveConfirmModal}
            setShowLeaveConfirmModal={setShowLeaveConfirmModal}
            callId={callId}
            jwt={jwt}
            onOpenChat={handleOpenChat}
            chatUnreadCount={unreadCount}
            onOpenShare={isHost ? handleOpenShare : undefined}
            onToggleTranscript={onToggleTranscript}
            isTranscriptOpen={isTranscriptOpen}
            isLeaving={isLeaving}
            isEnding={isEnding}
            onStartLeaving={onStartLeaving}
            onStartEnding={onStartEnding}
            resetExitState={resetExitState}
          />

          {showRaisedHandsModal ? (
            <RaisedHandsModal
              onClose={handleCloseRaisedHandsModal}
              raisedHandUserIds={raisedHandUserIds}
              isHost={isHost}
              onLowerHandForUser={lowerHandForUser}
            />
          ) : null}

          {showShareModal && callId && jwt ? (
            <ShareMeetingModal
              meetingId={callId}
              jwt={jwt}
              onClose={handleCloseShareModal}
            />
          ) : null}

          {participantsOpen ? (
            <ParticipantsOverlay
              onClose={onCloseParticipants}
              currentUserId={currentUserId}
              isHost={isHost}
              callId={callId}
              jwt={jwt}
              raisedHandUserIds={raisedHandUserIds}
              onLowerHandForUser={lowerHandForUser}
            />
          ) : null}

          {chatOpen ? (
            <ChatOverlay
              onClose={handleCloseChat}
              messages={messages}
              onSendMessage={sendMessage}
              removeMessage={removeMessageByClientId}
              connectionError={connectionError}
              connected={connected}
              reconnecting={reconnecting}
              inputDisabled={Boolean(connectionError)}
              currentUserId={currentUserId}
            />
          ) : null}

          {isTranscriptOpen ? (
            <TranscriptPanel
              segments={transcripts}
              onClose={onCloseTranscript}
              connected={transcriptConnected}
              reconnecting={transcriptReconnecting}
              connectionError={transcriptConnectionError}
              callId={callId}
              hasLeftRef={hasLeftRef}
              jwt={jwt}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default MeetingRoomContent;
