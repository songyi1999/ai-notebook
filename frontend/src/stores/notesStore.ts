import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Note {
    id: string;
    title: string;
    content: string;
    createdAt: string;
    updatedAt?: string;
}

interface NotesState {
    notes: Note[];
    activeNoteId: string | null;
    addNote: (note: Note) => void;
    updateNote: (id: string, updates: Partial<Note>) => void;
    deleteNote: (id: string) => void;
    setActiveNoteId: (id: string | null) => void;
    getNoteById: (id: string) => Note | undefined;
}

export const useNotesStore = create<NotesState>()(
    persist(
        (set, get) => ({
            notes: [],
            activeNoteId: null,

            addNote: (note) => set((state) => ({
                notes: [...state.notes, note],
                activeNoteId: note.id
            })),

            updateNote: (id, updates) => set((state) => ({
                notes: state.notes.map(note =>
                    note.id === id ? { ...note, ...updates, updatedAt: new Date().toISOString() } : note
                )
            })),

            deleteNote: (id) => set((state) => ({
                notes: state.notes.filter(note => note.id !== id),
                activeNoteId: state.activeNoteId === id ? null : state.activeNoteId
            })),

            setActiveNoteId: (id) => set({ activeNoteId: id }),

            getNoteById: (id) => get().notes.find(note => note.id === id)
        }),
        {
            name: 'notes-storage',
        }
    )
);