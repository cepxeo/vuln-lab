<?php
// A page fragment kept on disk between requests. A fragment that was changed
// is written back when the object goes away.
//
// This is the gadget of D9: an object of this class built by unserialize()
// writes any content to any path the web server may write.
class TemplateCache
{
    public $path;
    public $buffer = '';
    public $dirty = false;

    public function __construct(string $name)
    {
        $this->path = CACHE_DIR . '/' . $name . '.html';
    }

    public function get(): ?string
    {
        return is_file($this->path) ? (string) file_get_contents($this->path) : null;
    }

    public function put(string $html): void
    {
        $this->buffer = $html;
        $this->dirty = true;
    }

    public function __destruct()
    {
        if ($this->dirty && $this->path) {
            @file_put_contents($this->path, $this->buffer);
        }
    }
}
