;;; raises.el --- Run raises on the Python callable at point -*- lexical-binding: t -*-

(defun raises--project-root ()
  (or (locate-dominating-file default-directory "pyproject.toml")
      (locate-dominating-file default-directory "setup.py")
      default-directory))

(defun raises--module-path ()
  (let* ((root (raises--project-root))
         (rel  (file-relative-name (buffer-file-name) root))
         (bare (file-name-sans-extension rel)))
    (replace-regexp-in-string "[/\\\\]" "." bare)))

(defun raises--callable ()
  (or (python-info-current-defun)
      (error "raises: no Python def at point")))

(defun raises-at-point (target)
  "Run raises on TARGET (module.path:callable) and show results."
  (interactive
   (list (read-string "raises target: "
                      (format "%s:%s" (raises--module-path) (raises--callable)))))
  (let ((buf (get-buffer-create "*raises*")))
    (with-current-buffer buf
      (setq buffer-read-only nil)
      (erase-buffer)
      (if (zerop (call-process "raises" nil buf nil target))
          (message "raises: done")
        (message "raises: error — see *raises* buffer"))
      (setq buffer-read-only t))
    (display-buffer buf)))

(provide 'raises)
;;; raises.el ends here
