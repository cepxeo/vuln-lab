package com.harborline.claimdesk.web;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.File;
import java.nio.file.Files;
import java.util.List;
import java.util.Map;

@Controller
public class ClaimController {

    @Autowired
    private JdbcTemplate jdbc;

    @Value("${claimdesk.document-root}")
    private String documentRoot;

    private Sessions.User require(String sid) {
        Sessions.User u = Sessions.get(sid);
        if (u == null) throw new RuntimeException("not-authenticated");
        return u;
    }

    @GetMapping("/dashboard")
    public String dashboard(@CookieValue(value = "SID", required = false) String sid, Model model) {
        Sessions.User u = require(sid);
        model.addAttribute("user", u);
        model.addAttribute("claims",
            jdbc.queryForList("SELECT id, claim_no, title, status, amount FROM claims WHERE user_id = ?", u.id));
        return "dashboard";
    }

    // Broken access control: the claim is loaded by id with no owner check, so
    // any signed-in user can read any claim by walking the id.
    @GetMapping("/claim/{id}")
    public String claim(@PathVariable long id,
                        @CookieValue(value = "SID", required = false) String sid,
                        Model model) {
        require(sid);
        List<Map<String, Object>> rows =
            jdbc.queryForList("SELECT * FROM claims WHERE id = ?", id);
        if (rows.isEmpty()) { model.addAttribute("error", "No such claim"); return "claim"; }
        model.addAttribute("claim", rows.get(0));
        return "claim";
    }

    // Claim search. The term is concatenated into the WHERE clause (SQLi), and
    // the title/description are rendered with th:utext in search.html (stored/
    // reflected XSS).
    @GetMapping("/claims/search")
    public String search(@RequestParam(defaultValue = "") String q,
                        @CookieValue(value = "SID", required = false) String sid,
                        Model model) {
        require(sid);
        String sql = "SELECT id, claim_no, title, description, status FROM claims " +
                     "WHERE title LIKE '%" + q + "%' OR description LIKE '%" + q + "%'";
        model.addAttribute("q", q);
        try {
            model.addAttribute("results", jdbc.queryForList(sql));
        } catch (Exception e) {
            model.addAttribute("error", e.getMessage() + " [" + sql + "]");
        }
        return "search";
    }

    // Document download. The filename is joined to the document root with no
    // canonicalisation, so ../ escapes the directory (path traversal / LFI).
    @GetMapping("/document")
    public void document(@RequestParam String file,
                        @CookieValue(value = "SID", required = false) String sid,
                        HttpServletResponse resp) throws Exception {
        require(sid);
        File f = new File(documentRoot + "/" + file);
        resp.setHeader("Content-Disposition", "inline; filename=\"" + f.getName() + "\"");
        resp.setContentType("application/octet-stream");
        resp.getOutputStream().write(Files.readAllBytes(f.toPath()));
    }
}
