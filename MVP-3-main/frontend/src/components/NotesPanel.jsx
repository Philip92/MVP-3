import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import { toast } from 'sonner';
import { MessageSquare, Send, Loader2, Trash2, AtSign, X } from 'lucide-react';
import { format } from 'date-fns';

const API = `${window.location.origin}/api`;

export function NotesPanel({ entityType, entityId, buttonVariant = 'outline' }) {
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [open, setOpen] = useState(false);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showUserPicker, setShowUserPicker] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      fetchNotes();
      fetchTeamMembers();
    }
  }, [open, entityType, entityId]);

  const fetchNotes = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/notes`, {
        params: { entity_type: entityType, entity_id: entityId },
        withCredentials: true
      });
      setNotes(response.data);
    } catch (error) {
      console.error('Failed to fetch notes');
    } finally {
      setLoading(false);
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team`, { withCredentials: true });
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to fetch team members');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setSending(true);
    try {
      await axios.post(`${API}/notes`, {
        entity_type: entityType,
        entity_id: entityId,
        content: newNote,
        mentioned_users: selectedUsers.map(u => u.id)
      }, { withCredentials: true });
      
      setNewNote('');
      setSelectedUsers([]);
      fetchNotes();
      
      if (selectedUsers.length > 0) {
        toast.success(`Note added & ${selectedUsers.length} team member(s) notified`);
      } else {
        toast.success('Note added');
      }
    } catch (error) {
      toast.error('Failed to add note');
    } finally {
      setSending(false);
    }
  };

  const handleDelete = async (noteId) => {
    if (!confirm('Delete this note?')) return;
    try {
      await axios.delete(`${API}/notes/${noteId}`, { withCredentials: true });
      setNotes(notes.filter(n => n.id !== noteId));
      toast.success('Note deleted');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete note');
    }
  };

  const toggleUserSelection = (user) => {
    if (selectedUsers.find(u => u.id === user.id)) {
      setSelectedUsers(selectedUsers.filter(u => u.id !== user.id));
    } else {
      setSelectedUsers([...selectedUsers, user]);
    }
  };

  const insertMention = (userName) => {
    setNewNote(prev => prev + `@${userName} `);
    inputRef.current?.focus();
    setShowUserPicker(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant={buttonVariant} size="sm" className="gap-1">
          <MessageSquare className="h-4 w-4" />
          Notes
          {notes.length > 0 && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-xs">
              {notes.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="end">
        <div className="p-3 border-b bg-muted/50">
          <h4 className="font-medium text-sm flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Notes & Comments
          </h4>
          <p className="text-xs text-muted-foreground mt-1">
            Use @name to mention team members
          </p>
        </div>

        {/* Notes list */}
        <div className="max-h-64 overflow-y-auto p-3 space-y-3">
          {loading ? (
            <div className="text-center py-4">
              <Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" />
            </div>
          ) : notes.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-4">
              No notes yet
            </p>
          ) : (
            notes.map(note => (
              <div key={note.id} className="bg-muted/30 rounded-lg p-2.5 text-sm group">
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1">
                    <span className="font-medium text-xs text-primary">
                      {note.author_name}
                    </span>
                    <span className="text-xs text-muted-foreground ml-2">
                      {format(new Date(note.created_at), 'MMM d, h:mm a')}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDelete(note.id)}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </div>
                <p className="mt-1 whitespace-pre-wrap break-words">{note.content}</p>
                {note.mentioned_users?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {note.mentioned_users.map(userId => (
                      <Badge key={userId} variant="outline" className="text-xs px-1.5 py-0">
                        @{note.mentioned_user_names?.[userId] || 'User'}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Selected users */}
        {selectedUsers.length > 0 && (
          <div className="px-3 pb-2 flex flex-wrap gap-1">
            {selectedUsers.map(user => (
              <Badge
                key={user.id}
                variant="secondary"
                className="text-xs cursor-pointer hover:bg-destructive/20"
                onClick={() => toggleUserSelection(user)}
              >
                @{user.name} <X className="h-3 w-3 ml-1" />
              </Badge>
            ))}
          </div>
        )}

        {/* Team member picker */}
        {showUserPicker && (
          <div className="px-3 pb-2">
            <div className="bg-muted rounded-md p-2 max-h-32 overflow-y-auto">
              {teamMembers.map(member => (
                <button
                  key={member.id}
                  className="w-full text-left px-2 py-1 text-sm hover:bg-background rounded"
                  onClick={() => {
                    toggleUserSelection(member);
                    insertMention(member.name);
                  }}
                >
                  {member.name} <span className="text-muted-foreground text-xs">({member.role})</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-3 border-t flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={() => setShowUserPicker(!showUserPicker)}
            title="Mention team member"
          >
            <AtSign className="h-4 w-4" />
          </Button>
          <Input
            ref={inputRef}
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Add a note..."
            className="flex-1 text-sm"
          />
          <Button type="submit" size="icon" disabled={sending || !newNote.trim()}>
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </PopoverContent>
    </Popover>
  );
}

export default NotesPanel;
