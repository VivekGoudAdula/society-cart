import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

/**
 * Accessible Modal dialog with backdrop and escape key handling in warm cream palette.
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidthStyles = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#252824]/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Modal Box */}
      <div
        className={`relative w-full ${maxWidthStyles[maxWidth]} rounded-3xl bg-white p-6 sm:p-8 shadow-lifted border border-[#EBE8DF] transition-all z-10`}
      >
        <div className="flex items-start justify-between pb-4 border-b border-[#EBE8DF]/70">
          <div>
            {title && <h3 className="text-xl font-bold text-[#252824] tracking-tight">{title}</h3>}
            {description && <p className="mt-1 text-xs sm:text-sm text-[#827F76]">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-1.5 text-[#827F76] hover:bg-[#F3F0E8] hover:text-[#252824] transition-colors"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
};
