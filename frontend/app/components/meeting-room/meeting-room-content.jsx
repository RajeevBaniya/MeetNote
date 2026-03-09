"use client";

import { useState, useCallback } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

import useRaisedHands from "@/app/lib/meeting/use-raised-hands";
import { useMeetingChat } from "@/app/lib/meeting/use-meeting-chat";
import iconsData from "@/app/components/icons/icons.json";

import GalleryLayout from "./gallery-layout";
import ScreenShareLayout from "./screen-share-layout";
import MeetingControls from "./meeting-controls";
import RaisedHandsModal from "./raised-hands-modal";
import ParticipantsOverlay from "./participants-overlay";
import ChatOverlay from "./chat-overlay";

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
    isHandRaised,
  } = useRaisedHands(currentUserId);

  const [showRaisedHandsModal, setShowRaisedHandsModal] = useState(false);
  const [showLeaveConfirmModal, setShowLeaveConfirmModal] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const {
    messages,
    connected,
    connectionError,
    sendMessage,
    unreadCount,
    markChatRead,
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
    const res = await fetch(`${apiUrl}/meetings/${callId}/end`, {
      method: "POST",
      headers: { Authorization: `Bearer ${jwt}` },
    });
    return res.ok;
  }, [callId, jwt]);

  const handleOpenRaisedHandsModal = useCallback(() => {
    setShowRaisedHandsModal(true);
  }, []);

  const handleCloseRaisedHandsModal = useCallback(() => {
    setShowRaisedHandsModal(false);
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
          />

          {showRaisedHandsModal ? (
            <RaisedHandsModal
              onClose={handleCloseRaisedHandsModal}
              raisedHandUserIds={raisedHandUserIds}
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
            />
          ) : null}

          {chatOpen ? (
            <ChatOverlay
              onClose={handleCloseChat}
              messages={messages}
              onSendMessage={sendMessage}
              connectionError={connectionError}
              connected={connected}
              inputDisabled={Boolean(connectionError)}
              currentUserId={currentUserId}
            />
          ) : null}

          {/* Waiting room UI removed */}
        </div>
      </div>
    </div>
  );
};

export default MeetingRoomContent;
