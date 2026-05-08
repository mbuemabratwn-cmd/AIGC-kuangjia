interface FileSystemDirectoryHandle {
  name: string;
}

interface Window {
  showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
}
